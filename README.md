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


### **Repository structure**
<hr style="border: 1px solid black; margin: 0;">  

The architecture of the ```fimpef``` integrates different modules to which helps the automation of flood evaluation. All those modules codes are in source (```src``` ) folder.
```bash
Benchmark_FIM_Database/     
├── FIM/                       # Documentation (contains 'FIMserv' Tool usage sample codes)
│   └── sampledata/              # Contains the sample data to demonstrate how this frameworks works    
│   └── fimpef_usage.ipynb            #Sample code usage of the Evaluation framework
├── Images/                       # have sample images for documentation       
├── src/
│   └── fimpef/         
│       ├──BuildingFootprint/ # Contains the evaluation of model predicted FIM with microsoft building footprint
│       │   └── evaluationwithBF.py       
│       └── ContingencyMap/      # Contains all the metrics calculation and contingency map generation
│           ├── evaluationFIM.py # main evaluation moodule 
│           └── methods.py  # Contains 3 different methods of evaluation 
│           └── metrics.py  # metrics calculation module
│           └── plotevaluationmetrics.py  # use to vizualize the different performance metrics
│           └── printcontingency.py  # prints the contingency map to quickly generate the Map layout
│           └── PWBs3.py  # module which helps to get permanent water bodies from s3 bucket
└── tests/                  # Includes test cases for different functionality
```
