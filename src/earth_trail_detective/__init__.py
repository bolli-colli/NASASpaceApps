"""Earth Trail Detective – follow a pollutant through the water cycle.

The package follows a layered architecture (dependencies point inwards only):

    presentation  ->  application  ->  domain  <-  infrastructure

* ``domain``          pure business rules: entities, statistics, units (no I/O)
* ``application``     use cases that orchestrate the domain through ports
* ``infrastructure``  adapters for YAML, Parquet, CSV and NASA Earthdata
* ``presentation``    the Streamlit user interface
"""

APP_NAME = "Earth Trail Detective"
__version__ = "0.1.0"
