import os
import folium
import fiona
import json
import warnings
import contextlib
import sys
import requests
from io import StringIO
import pandas as pd
from datetime import datetime
from pathlib import Path
import numpy as np
import geopandas as gpd
from datetime import datetime, timedelta
import calendar
import random
import fimeval as fe
from shapely.errors import ShapelyDeprecationWarning
from shapely.geometry import shape, LineString, MultiLineString, box
from folium import MacroElement
from jinja2 import Template

from fim_db import *

#TO MERGE LEVEL WISE SHAPEFILE INTO THE GEOJSON FOR THE VIZUALIZATION
def read_gpkgs(folder_path, target_crs="EPSG:4326"):
    gdfs = []

    for root, _, files in os.walk(folder_path):
        for file in files:
            if file.endswith(".gpkg"):
                gpkg_path = os.path.join(root, file)
                try:
                    layers = fiona.listlayers(gpkg_path)
                    for layer in layers:
                        gdf = gpd.read_file(gpkg_path, layer=layer)
                        gdf = gdf.to_crs(target_crs)
                        gdfs.append(gdf)
                except Exception as e:
                    print(f"Failed to read {gpkg_path}: {e}")
    return gdfs

def merge_and_save_geojson(gdfs, output_path, crs="EPSG:4326"):
    if gdfs:
        merged_gdf = pd.concat(gdfs, ignore_index=True)
        merged_gdf = gpd.GeoDataFrame(merged_gdf, crs=crs)
        merged_gdf.to_file(output_path, driver="GeoJSON")
        print(f"Saved merged GeoJSON: {output_path}")
    else:
        print(f"No valid GeoDataFrames to save for: {output_path.name}")

def getLevelWiseGeoJSON(main_dir, out_dir):
    main_dir = Path(main_dir)
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    for folder in main_dir.iterdir():
        if folder.is_dir():
            print(f"Processing folder: {folder.name}")
            gdfs = read_gpkgs(folder)
            out_path = out_dir / f"{folder.name}.geojson"
            merge_and_save_geojson(gdfs, out_path)

LEVEL_COLOR_MAP = {
    "Level_1": "#08306b",   # Dark Blue
    "Level_2": "#238b45",   # Green
    "Level_3": "#6a51a3",   # Purple
    "Level_4": "#ec7014"    # Orange
}

@contextlib.contextmanager
def suppress_stderr():
    with open(os.devnull, "w") as fnull:
        stderr = sys.stderr
        sys.stderr = fnull
        try:
            yield
        finally:
            sys.stderr = stderr

def clean_gdf(gdf):
    cleaned = gdf.copy()
    for col in cleaned.columns:
        if col == "geometry":
            continue
        if pd.api.types.is_datetime64_any_dtype(cleaned[col]):
            cleaned[col] = cleaned[col].astype(str)
        elif cleaned[col].apply(lambda x: isinstance(x, (dict, list))).any():
            print(f"Dropping unsupported column: {col}")
            cleaned.drop(columns=[col], inplace=True)
    return cleaned

def make_popup_html(props, bucket_name="sdmlab"):
    html = "<table style='width:100%; font-size:12px;'>"
    for key, val in props.items():
        if key != "geometry":
            html += f"<tr><th style='text-align:left'>{key}</th><td>{val}</td></tr>"

    level = props.get("Level")
    dms_code = props.get("DMS_Code_centroid")
    file_name = props.get("File_Name")
    flood_date = props.get("Date of the Flood")

    if flood_date and dms_code:
        folder_name = f"{flood_date}_{dms_code}"
    else:
        folder_name = None

    if level and folder_name and file_name:
        s3_path = f"FIM_Database/{level}/{folder_name}/{file_name}"
        s3_url = f"https://{bucket_name}.s3.amazonaws.com/{s3_path}"
        html += f"<tr><td colspan='2'><a href='{s3_url}' target='_blank' download>⬇ Download TIFF</a></td></tr>"
    else:
        html += "<tr><td colspan='2' style='color:red;'>File info missing</td></tr>"

    html += "</table>"
    return html
    
def getFIMavailAOIs(main_dir, user_AOI=None, bucket_name="sdmlab"):
    main_dir = Path(main_dir)
    geojson_files = list(main_dir.glob("*.geojson"))

    if not geojson_files:
        print("No .geojson files found.")
        return

    gdfs = []
    total_bounds = [float("inf"), float("inf"), float("-inf"), float("-inf")]

    for file in geojson_files:
        try:
            with suppress_stderr():
                gdf = gpd.read_file(file)
            gdf = clean_gdf(gdf)
            gdfs.append((file.stem, gdf))

            minx, miny, maxx, maxy = gdf.total_bounds
            total_bounds[0] = min(total_bounds[0], minx)
            total_bounds[1] = min(total_bounds[1], miny)
            total_bounds[2] = max(total_bounds[2], maxx)
            total_bounds[3] = max(total_bounds[3], maxy)

        except Exception as e:
            print(f"Failed to read {file.name}: {e}")

    avg_lat = (total_bounds[1] + total_bounds[3]) / 2
    avg_lon = (total_bounds[0] + total_bounds[2]) / 2

    fmap = folium.Map(location=[avg_lat, avg_lon], zoom_start=4.5)

    folium.TileLayer("OpenStreetMap").add_to(fmap)
    folium.TileLayer("CartoDB Positron").add_to(fmap)
    folium.TileLayer(
        tiles="https://services.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
        name="Satellite Imagery",
        attr="Tiles © Esri"
    ).add_to(fmap)

    for name, gdf in gdfs:
        try:
            level = name  # e.g., Level_3
            color = LEVEL_COLOR_MAP.get(level, "#999999")
            style_function = lambda feature, color=color: {
                'fillOpacity': 0.5,
                'weight': 1.5,
                'color': color
            }

            layer_group = folium.FeatureGroup(name=level, show=True)

            for _, row in gdf.iterrows():
                feature = {
                    "type": "Feature",
                    "geometry": row.geometry.__geo_interface__,
                    "properties": row.drop("geometry").to_dict()
                }

                popup_html = make_popup_html(feature["properties"], bucket_name)

                gj = folium.GeoJson(
                    data=feature,
                    style_function=style_function
                )
                gj.add_child(folium.Popup(popup_html, max_width=400))
                gj.add_to(layer_group)

            layer_group.add_to(fmap)

        except Exception as e:
            print(f"Could not add layer {name}: {e}")

    if user_AOI:
        try:
            with suppress_stderr():
                user_gdf = gpd.read_file(user_AOI)
            if user_gdf.crs is None:
                user_gdf.set_crs(epsg=4326, inplace=True)
            elif user_gdf.crs.to_epsg() != 4326:
                user_gdf = user_gdf.to_crs(epsg=4326)
            user_gdf = clean_gdf(user_gdf)

            user_layer = folium.FeatureGroup(name="User AOI", show=True)
            for _, row in user_gdf.iterrows():
                folium.GeoJson(
                    data=row.geometry,
                    style_function=lambda x: {'color': 'red', 'weight': 2, 'fillOpacity': 0.1}
                ).add_to(user_layer)
            user_layer.add_to(fmap)

        except Exception as e:
            print(f"Could not load user AOI: {e}")

    folium.LayerControl(collapsed=False).add_to(fmap)
    return fmap

#WRAP ALL THE VIZUALIZATION MODULE WHICH AUTOMATICALLY GETS THE AOI INFORMATION FORM S3 DATABASE
##Jupyter Notebook
#def VizualizeFIMavailAOIs(boundary_dir=None):
    #tmp_dir, geojson_files = AOIs_inS3(s3, bucket_name)
    #fmap = getFIMavailAOIs(tmp_dir, boundary_dir)
    #return fmap

def VizualizeFIMavailAOIs(boundary_dir=None, output_html="FIM_AOIs_Visualization.html"):
    tmp_dir, geojson_files = AOIs_inS3(s3, bucket_name)
    fmap = getFIMavailAOIs(tmp_dir, boundary_dir)

    # Save the map without any download button
    fmap.save(output_html)
    print(f"Map saved to {output_html}")

    return output_html

    
#FIND ALL THE FLOOD EVENT THAT INTERSECTED WITH THE USER DEFINED BOUNDARY
def GetIntersectedAOISummary(user_boundary_path, s3_client=s3, bucket=bucket_name, prefix="FIM_Database/Levelwise_AOIs/"):
    warnings.filterwarnings("ignore", category=ShapelyDeprecationWarning)

    with suppress_stderr():
        user_gdf = gpd.read_file(user_boundary_path)

    if user_gdf.crs is None:
        user_gdf.set_crs(epsg=4326, inplace=True)
    elif user_gdf.crs.to_epsg() != 4326:
        user_gdf = user_gdf.to_crs(epsg=4326)

    user_geom = user_gdf.geometry.union_all()

    tmp_dir, geojson_files = AOIs_inS3(s3_client, bucket, prefix)
    output_blocks = []

    for geojson_file in geojson_files:
        try:
            with suppress_stderr():
                gdf = gpd.read_file(geojson_file)

            gdf = gdf.to_crs(epsg=4326)
            gdf["__layername__"] = Path(geojson_file).stem

            intersecting = gdf[gdf.geometry.intersects(user_geom)].copy()
            if not intersecting.empty:
                for _, row in intersecting.iterrows():
                    block = []
                    layername = row.get("__layername__", "").strip()
                    location = row.get("Location", "").strip()
                    block.append(f"{location} flood")
                    block.append("---------------------------")
                    block.append(f"Benchmark FIM filename - {row.get('File_Name', '').strip()}")

                    # Only include Date of Flood if not Level_4
                    if "Level_4" not in layername:
                        block.append(f"Date of Flood event - {row.get('Date_of_Flood', '')}")

                    block.append(f"Title - {row.get('Title', '').strip()}")
                    block.append(f"Source - {row.get('Source', '').strip()}")
                    block.append(f"Data Quality - {row.get('Data_Quality', '').strip()}")
                    block.append(f"Level - {layername}")
                    output_blocks.append("\n".join(block))
        except Exception:
            continue

    if output_blocks:
        return "\n\n".join(output_blocks)
    else:
        return "No intersecting retrospective flood AOI found."
    
#EVALUATE FIM USING THE BENCHMARK FROM BUCKET
def EvaluateFIMwithBM(
    candidate_dir, filename, level,
    method_name, output_dir,
    PWB_dir=None, shapefile_dir=None,
    target_crs=None, target_resolution=None,
):

    candidate_dir = Path(candidate_dir)
    main_dir = candidate_dir
    
    #Get the benchmark FIM
    _ = get_benchmark_FIM(
        filename=filename,
        level=level,
        candidate_raster=main_dir,
    )

    # Call existing EvaluateFIM
    fe.EvaluateFIM(
        main_dir=main_dir,
        method_name=method_name,
        output_dir=output_dir,
        PWB_dir=PWB_dir,
        shapefile_dir=shapefile_dir,
        target_crs=target_crs,
        target_resolution=target_resolution
    )