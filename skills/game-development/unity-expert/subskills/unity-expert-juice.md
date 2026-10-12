# /unity-expert-juice - Camera Juicing, Dynamic FOV & Screenshake

Sarsıcı oyuncu geri bildirimi ve sinematik hız hissi.

## Juicing Mekanikleri

1. **Speed FOV Stretch**: `FOV = Lerp(FOV_min, FOV_max, InverseLerp(V_min, V_max, V_player))` + smooth damping.
2. **Trauma Bazlı Screenshake**: `Intensity = Trauma^2`; rumble için Perlin noise, sert darbeler için harmonik sönümlü sinüs dalgası.
3. **Impact Hitstop**: `0.03s - 0.08s` mikro duraklatma (unscaled time) ile darbe ağırlığı hissi.
4. **Şerit Geçişi Roll Banking**: Hızlı kaçış manevralarında dinamik roll `θ_roll = -k * v_x`.

## Referans Dokümanlar
- [`camera_juicing_and_screen_shake.md`](../researches/camera_juicing_and_screen_shake.md)
- [`camera_positioning_math.md`](../researches/camera_positioning_math.md)
