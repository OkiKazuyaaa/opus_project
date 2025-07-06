#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import pandas as pd
import geopandas as gpd
from shapely.geometry import Point
import folium
from folium import GeoJson
import branca.colormap as cm

# ───── 設定 ─────
INPUT_FILE  = "huff_step3_all_in_one.xlsx"
SHEET        = "flows_detail"
OUTPUT_HTML = "catchment_on_click.html"

# 1) Load and pick the winning store for each origin
df = pd.read_excel(INPUT_FILE, sheet_name=SHEET)
# 必要列チェック…
idx = df.groupby("origin_id")["P_ij"].idxmax()
df_win = df.loc[idx, ["origin_id","origin_lat","origin_lon","store"]].reset_index(drop=True)

# 2) Make GeoDataFrame of the _points_ (origins)
gdf_pts = gpd.GeoDataFrame(
    df_win,
    geometry=df_win.apply(lambda r: Point(r["origin_lon"], r["origin_lat"]), axis=1),
    crs="EPSG:4326"
)

# 3) Make GeoDataFrame of the _polygons_ (catchment areas)
#    We assume you already have a GeoDataFrame of polygons (one per origin_id).
#    If you don't yet, you can buffer each point or load a precomputed one:
#    for demo: buffer 500m around the point…
gdf_poly = gdf_pts.copy()
gdf_poly["geometry"] = gdf_poly.geometry.buffer(0.005)  # ≈500m buffer for demo
gdf_poly.crs = "EPSG:4326"

# 4) Assign a numerical code to each store & build a colormap
gdf_pts["code"]     = gdf_pts["store"].astype("category").cat.codes
gdf_poly["code"]    = gdf_pts["code"]
stores              = list(gdf_pts["store"].astype("category").cat.categories)
cmap                = cm.linear.Paired_09.scale(0, len(stores)-1).to_step(len(stores))
cmap.caption        = "獲得ストア"

# 5) Build the map
m = folium.Map(location=[gdf_pts["origin_lat"].mean(), gdf_pts["origin_lon"].mean()], zoom_start=13)
cmap.add_to(m)

# 6) Add each polygon to the map, but keep it _hidden_ initially
poly_layers = {}
for _, row in gdf_poly.iterrows():
    store   = row["store"]
    origin  = row["origin_id"]
    code    = int(row["code"])
    gj = GeoJson(
        data=row["geometry"].__geo_interface__,
        style_function=lambda feat, col=cmap(code): {
            "fillColor": col, "color": col, "weight": 2, "fillOpacity": 0.4
        }
    )
    gj.add_to(m)
    gj.layer_name = f"poly-{origin}"
    gj.hide = True
    poly_layers[origin] = gj

# 7) Add the pins, binding a popup and a _small_ bit of JS to toggle its polygon
for _, row in gdf_pts.iterrows():
    origin = row["origin_id"]
    folium.Marker(
        location=[row["origin_lat"], row["origin_lon"]],
        icon=folium.Icon(color="blue", icon="home"),
        popup=folium.Popup(f"起点ID: {origin}<br>店舗: {row['store']}", max_width=200),
    ).add_to(m).add_child(
        folium.Element(f"""
        <script>
          this.on('click', function(e) {{
            var layer = window._layers['poly-{origin}'];
            if (!layer) return;
            if (map.hasLayer(layer)) {{
              map.removeLayer(layer);
            }} else {{
              map.addLayer(layer);
            }}
          }});
        </script>
        """)
    )

# 8) expose our polygon layers in a JS variable for the above script
m.get_root().html.add_child(folium.Element("""
  <script>
    window._layers = {};
    for (var i in map._layers) {
      var l = map._layers[i];
      if (l.feature && l.feature.geometry.type!=="Point") {
        window._layers[l.options.layerName] = l;
      }
    }
  </script>
"""))

m.save(OUTPUT_HTML)
print(f"Done → {OUTPUT_HTML}")
