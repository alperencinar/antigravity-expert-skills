# /3d-asset-polish - Blender Split, Symmetrize & Scale

Üretilen Meshy modelini Blender'da işle: tekerlekleri ayır, koordinatları merkeze/zemine oturt, gerçekçi oyun ölçeklerine getir.

`process_model.py` yaz ve headless çalıştır: `blender --background --python process_model.py`

## İşlem Sırası

1. **Sahne reset & import**: `bpy.ops.wm.read_factory_settings(use_empty=True)` + FBX/GLB import.
2. **Geçici join & merkezleme**: Tüm meshleri birleştir, `ORIGIN_GEOMETRY / BOUNDS` ile merkezle, `location = (0,0,0)` ve transform apply.
3. **+90° Z rotasyonu**: Araç önü Blender'da +Y'ye (Unity'de +Z Forward) baksın; transform apply ile sabitle.
4. **Loose parts ayrımı**: `bpy.ops.mesh.separate(type='LOOSE')` — tekerlek göreli konumları wheel well içinde %100 kilitli kalır.
5. **Sağlam tekerlek partisyonlama**: Silindirik şekil kontrolü (`0.12m - 0.20m` çap aralığı) veya isimde "wheel"; hem low-poly (30-80 vertex) hem high-poly (15k vertex) modellerle uyumlu.
6. **Prop vs Araç ayrımı**:
   - Tekerlek yoksa (ağaç/bina/köprü): tüm parçaları join et, pivotu MUTLAK ALT TABANA (`min_z`) al → Unity'de anında `Y=0` yerleşim.
   - Tekerlek varsa: gövde parçalarını `body` olarak join et; her tekerleğin origin'ini `ORIGIN_GEOMETRY / BOUNDS` ile merkezle ve `wheel-{front|back}-{left|right}` adlandır.
7. **Temiz FBX export**: `axis_forward='-Z'`, `axis_up='Y'`, `bake_space_transform=True`, `apply_scale_options='FBX_SCALE_ALL'`, sadece `{'MESH'}`.

Tam Python betiği için ana [`SKILL.md`](../SKILL.md) Bölüm 3'e bakınız.

## Referans Dokümanlar
- [`blender_reference_modeling.md`](../researches/blender_reference_modeling.md)
- [`vertex_color_ao.md`](../researches/vertex_color_ao.md)
- [`3d_asset_pipeline.md`](../researches/3d_asset_pipeline.md)
