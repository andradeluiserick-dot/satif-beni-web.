import io
import json
import sys
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from core import parse_hotspots, attribute_municipalities, to_geojson, to_kmz, to_shapefile_zip

class CoreTest(unittest.TestCase):
    def setUp(self):
        self.df=parse_hotspots(io.StringIO('latitude,longitude,acq_date,acq_time,frp,satellite\n-13,-65,2026-11-17,0530,12.5,X\n-14,-64,2026-11-17,2355,21,X\n'))
        self.polys={'type':'FeatureCollection','features':[
          {'type':'Feature','properties':{'nombre_mun':'Ejemplo','nombre_prov':'Provincia de prueba','idep':'08'},
           'geometry':{'type':'Polygon','coordinates':[[[-66,-14],[-64,-14],[-64,-12],[-66,-12],[-66,-14]]]}}]}
    def test_parse(self):
        self.assertEqual(len(self.df),2)
        self.assertEqual(self.df.iloc[0]['hora_utc'],'05:30')
    def test_clip(self):
        clipped=attribute_municipalities(self.df,self.polys)
        self.assertEqual(len(clipped),2) # ambos puntos en el borde o interior
        self.assertEqual(clipped.iloc[0]['municipio'],'Ejemplo')
    def test_exports(self):
        clipped=attribute_municipalities(self.df,self.polys)
        self.assertEqual(len(json.loads(to_geojson(clipped))['features']),2)
        self.assertGreater(len(to_kmz(clipped)),100)
        self.assertGreater(len(to_shapefile_zip(clipped)),100)

if __name__ == '__main__': unittest.main()
