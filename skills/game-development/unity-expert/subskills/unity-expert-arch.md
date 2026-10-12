# /unity-expert-arch - FSM State Machine & Solvable Traffic Generation

Temiz, interface-driven oyun akışı ve çözülebilir (solvable) prosedürel spawn mimarisi.

## Ana Mimari Bileşenler

1. **State Machine (`IGameState` & `GameContext`)**
   - `IntroState`: Pool prewarm, kamera countdown flyby.
   - `GameplayState`: Oyuncu kontrolü, hız bazlı skor, near-miss takibi.
   - `BulletTimeState`: Matrix slow-motion eğrisi (`Time.timeScale = 0.35f`).
   - `CrashState`: Çarpma anı freeze frame, araç ezilmesi (crumple), ragdoll.
   - `ReviveState`: 50m engel temizleme taraması, 3sn dokunulmazlık kalkanı.
2. **Solvable Traffic Solver (`TrafficSpawnValidator`)**
   - Batch spawn commit edilmeden önce matematiksel çözülebilirlik garantisi:
     - `T_arrive = ΔZ / (V_player - V_traffic)`
     - Kural: `T_switch < T_arrive - ε_reflex`
3. **Floating Origin Reset (`FloatingOriginHandler`)**
   - Oyuncu `Z > 1000m` olduğunda tüm transformlara `ΔZ = -1000m` shift yayını; float32 vertex jitter ve kamera stutter'ı sıfırlanır.

## Referans Dokümanlar
- [`endless_runner_state_and_generation_systems.md`](../researches/endless_runner_state_and_generation_systems.md)
- [`endless_runner_architecture_blueprint.md`](../researches/endless_runner_architecture_blueprint.md)
- [`realtime_escape_matrix_and_spawn_pacing.md`](../researches/realtime_escape_matrix_and_spawn_pacing.md)
- [`spawn_pacing_danger_zone_analysis_report.md`](../researches/spawn_pacing_danger_zone_analysis_report.md)
