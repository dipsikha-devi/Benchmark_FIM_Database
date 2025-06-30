# Benchmark FIM Database
The Benchmark Flood Inundation Mapping (FIM) Database comprises of remote sensing-derived and high-fidelity model-predicted FIMs. The FIM inventory is classified into four quality-based levels (Figure 1). The database is stored in an AWS S3 bucket with an open API. Each folder in the S3 Bucket includes:<br>
(a) A flood inundation raster (GeoTIFF; <code>.tiff</code>)<br>
(b) A vector layer illustrating the bounding box of the flood domain (within a Geopackage; <code>.gpkg</code>)<br>
(c) Metadata file (JSON; <code>.json</code>)

</ul>
Visualization and downloading from the S3 Bucket is enabled through a Jupyter Notebook (included in this repository).  
<p align="center">
  <img src="https://github.com/user-attachments/assets/fbbeb567-eddc-44d3-9f7e-86d781f9ce54" width="600" alt="image" />
</p>

<p align="center"><b>Figure 1. The Benchmark FIM Database Overview</b></p>



