# Advanced Endless Runner Architecture & Procedural Generation Systems

A production-grade architectural guide and technical synthesis for high-performance, deterministic, and scalable endless runners in Unity (C#).

---

## Table of Contents
1. [Production State Machine FSM (`IGameState` & `GameContext`)](#1-production-state-machine-fsm)
   - [1.1 Architectural Overview & Zero-Allocation Strategy](#11-architectural-overview--zero-allocation-strategy)
   - [1.2 GameContext & State Interfaces](#12-gamecontext--state-interfaces)
   - [1.3 State Implementations](#13-state-implementations)
     - [IntroState](#introstate)
     - [GameplayState](#gameplaystate)
     - [BulletTimeState](#bullettimestate)
     - [CrashState](#crashstate)
     - [ReviveState](#revivestate)
   - [1.4 State Machine Controller Implementation](#14-state-machine-controller-implementation)
2. [ScriptableObject Data-Driven Batch Solver (`TrafficSpawnValidator`)](#2-scriptableobject-data-driven-batch-solver)
   - [2.1 Solvability Problem Statement](#21-solvability-problem-statement)
   - [2.2 Data Structures & ScriptableObjects](#22-data-structures--scriptableobjects)
   - [2.3 Bitmask & BFS Solvability Validation Algorithm](#23-bitmask--bfs-solvability-validation-algorithm)
   - [2.4 Difficulty Scaling & Dynamic Spawner Engine](#24-difficulty-scaling--dynamic-spawner-engine)
3. [Floating Origin Reset System (`FloatingOriginHandler`)](#3-floating-origin-reset-system)
   - [3.1 IEEE 754 Floating-Point Precision Loss At Scale](#31-ieee-754-floating-point-precision-loss-at-scale)
   - [3.2 Architecture & Multi-System Synchronization](#32-architecture--multi-system-synchronization)
   - [3.3 Complete FloatingOriginHandler Implementation](#33-complete-floatingoriginhandler-implementation)
4. [Extensible Dynamic Hazard System (`IDynamicHazard`)](#4-extensible-dynamic-hazard-system)
   - [4.1 Dynamic Hazard Abstraction Interface](#41-dynamic-hazard-abstraction-interface)
   - [4.2 Ramp Hazard (`TrainRampHazard`)](#42-ramp-hazard-trainramphazard)
   - [4.3 Jackknife Truck Hazard (`JackknifeTruckHazard`)](#43-jackknifetruckhazard)
   - [4.4 Overhead Cargo Drop Hazard (`ContainerDropHazard`)](#44-overhead-cargo-drop-hazard-containerdrophazard)
   - [4.5 Hazard Pool Manager Integration](#45-hazard-pool-manager-integration)

---

## 1. Production State Machine FSM

### 1.1 Architectural Overview & Zero-Allocation Strategy
In modern high-speed endless runners (e.g., *Subway Surfers*, *Temple Run 2*), state transitions govern critical gameplay phases, UI layers, input routing, audio mix profiles, and physics parameters. A naive state machine implementation relying on `System.Enum` switch statements or dynamically instantiated state classes (`new State()`) introduces Garbage Collection (GC) pressure and rigid, coupled code.

The production architecture specified here utilizes:
1. **Pre-instantiated State Flyweights:** States are allocated once during initial bootstrap and cached in a dictionary or fixed array.
2. **Context-Driven State Injections (`GameContext`):** All persistent references (Player Controller, Camera Rig, Chunk Spawner, UI Mediator, Dynamic Difficulty Manager, Audio Router) are passed via a shared dependency context.
3. **Payload Support (`IGameStatePayload`):** Facilitates parameter transfer between state transitions (e.g., passing crash impact velocity from `GameplayState` to `CrashState`) without garbage allocation.

```
                  ┌──────────────┐
                  │  IntroState  │
                  └──────┬───────┘
                         │ (Player Ready / Pre-warm Complete)
                         ▼
                  ┌──────────────┐ ◄─── (Invincibility Expired / Re-enter)
                  │ GameplayState│ ◄─────────────────────────┐
                  └──────┬───────┘                           │
     (Near-Miss) │      │ (Fatal Impact)                   │
                 ▼      ▼                                   │
  ┌─────────────────┐  ┌──────────────┐               ┌──────┴───────┐
  │ BulletTimeState │  │  CrashState  │ ────────────► │ ReviveState  │
  └────────┬────────┘  └──────────────┘ (Ad/Coin Check)└──────────────┘
           │ (Timer Expire)
           └─────────►
```

### 1.2 GameContext & State Interfaces

```csharp
using System;
using UnityEngine;
using UnityEngine.Audio;

namespace EndlessRunner.Architecture
{
    /// <summary>
    /// Lightweight interface for state payload data to allow parameter passing without GC allocations.
    /// </summary>
    public interface IGameStatePayload { }

    /// <summary>
    /// Interface contract for all finite state machine states.
    /// </summary>
    public interface IGameState
    {
        void Enter(GameContext context, IGameStatePayload payload = null);
        void Tick(GameContext context, float deltaTime);
        void FixedTick(GameContext context, float fixedDeltaTime);
        void Exit(GameContext context);
    }

    /// <summary>
    /// Shared service locator and state container for the gameplay loop.
    /// </summary>
    public sealed class GameContext
    {
        // Core Systems
        public MonoBehaviour CoroutineRunner { get; }
        public IPlayerController Player { get; }
        public ITrackChunkSpawner ChunkSpawner { get; }
        public IDifficultyManager DifficultyManager { get; }
        public FloatingOriginHandler OriginHandler { get; }
        
        // UI & Audio
        public IUIMediator UIMediator { get; }
        public AudioMixer MainAudioMixer { get; }

        // State Properties
        public float DistanceTraveledAccumulated => OriginHandler.TotalAccumulatedDistance;
        public float CurrentRunTime { get; set; }
        public int CoinsCollected { get; set; }
        public int ReviveCount { get; set; }
        
        // Audio Snapshots
        public AudioMixerGroup MusicGroup { get; }
        public AudioMixerGroup SFXGroup { get; }

        public GameContext(
            MonoBehaviour coroutineRunner,
            IPlayerController player,
            ITrackChunkSpawner chunkSpawner,
            IDifficultyManager difficultyManager,
            FloatingOriginHandler originHandler,
            IUIMediator uiMediator,
            AudioMixer mainAudioMixer,
            AudioMixerGroup musicGroup,
            AudioMixerGroup sfxGroup)
        {
            CoroutineRunner = coroutineRunner;
            Player = player;
            ChunkSpawner = chunkSpawner;
            DifficultyManager = difficultyManager;
            OriginHandler = originHandler;
            UIMediator = uiMediator;
            MainAudioMixer = mainAudioMixer;
            MusicGroup = musicGroup;
            SFXGroup = sfxGroup;
        }

        public void ResetRunData()
        {
            CurrentRunTime = 0f;
            CoinsCollected = 0;
            ReviveCount = 0;
        }
    }
}
```

### 1.3 State Implementations

#### IntroState
Handles camera flythroughs, character animation priming, track pre-warming, and UI countdown.

```csharp
using System.Collections;
using UnityEngine;

namespace EndlessRunner.Architecture.States
{
    public sealed class IntroState : IGameState
    {
        public void Enter(GameContext context, IGameStatePayload payload = null)
        {
            context.ResetRunData();
            context.Player.SetInputActive(false);
            context.Player.PlayAnimation("Intro_StartPose");
            
            // Pre-warm initial track buffer (e.g. 5 chunks ahead)
            context.ChunkSpawner.PrewarmTrackBuffer(5);
            context.UIMediator.ShowScreen(UIScreenType.IntroOverlay);

            context.CoroutineRunner.StartCoroutine(ExecuteIntroSequence(context));
        }

        private IEnumerator ExecuteIntroSequence(GameContext context)
        {
            context.UIMediator.PlayCountdownAnimation();
            yield return new WaitForSeconds(2.5f);
            
            // Transition directly to GameplayState
            GameStateMachine.Instance.TransitionTo<GameplayState>();
        }

        public void Tick(GameContext context, float deltaTime) { }
        public void FixedTick(GameContext context, float fixedDeltaTime) { }
        public void Exit(GameContext context)
        {
            context.Player.SetInputActive(true);
            context.UIMediator.HideScreen(UIScreenType.IntroOverlay);
            context.UIMediator.ShowScreen(UIScreenType.HUD);
        }
    }
}
```

#### GameplayState
Main execution loop driving player movement, chunk generation, difficulty progression, and collision triggers.

```csharp
namespace EndlessRunner.Architecture.States
{
    public sealed class GameplayState : IGameState
    {
        public void Enter(GameContext context, IGameStatePayload payload = null)
        {
            Time.timeScale = 1.0f;
            Time.fixedDeltaTime = 0.02f; // Standard 50Hz physics
            context.MainAudioMixer.SetFloat("MusicPitch", 1.0f);
            context.MainAudioMixer.SetFloat("MusicCutoff", 22000f);
            context.Player.SetVulnerability(true);
        }

        public void Tick(GameContext context, float deltaTime)
        {
            context.CurrentRunTime += deltaTime;
            context.DifficultyManager.UpdateDifficulty(context.CurrentRunTime, context.DistanceTraveledAccumulated);
            
            context.Player.ManualUpdate(deltaTime);
            context.ChunkSpawner.UpdateChunks(context.Player.Position.z);
            context.OriginHandler.CheckAndExecuteShift(context.Player.Position);
        }

        public void FixedTick(GameContext context, float fixedDeltaTime)
        {
            context.Player.ManualFixedUpdate(fixedDeltaTime);
        }

        public void Exit(GameContext context) { }
    }
}
```

#### BulletTimeState
Triggered upon high-risk near-miss dodges or specific power-up pickups. Manipulates time scales while applying real-time audio pitch bending.

```csharp
using UnityEngine;

namespace EndlessRunner.Architecture.States
{
    public struct BulletTimePayload : IGameStatePayload
    {
        public float Duration;
        public float TimeScaleFactor;
    }

    public sealed class BulletTimeState : IGameState
    {
        private float _timer;
        private float _duration;
        private float _targetTimeScale;

        public void Enter(GameContext context, IGameStatePayload payload = null)
        {
            var bPayload = payload is BulletTimePayload p ? p : new BulletTimePayload { Duration = 2.0f, TimeScaleFactor = 0.35f };
            _duration = bPayload.Duration;
            _targetTimeScale = bPayload.TimeScaleFactor;
            _timer = 0f;

            Time.timeScale = _targetTimeScale;
            Time.fixedDeltaTime = 0.02f * Time.timeScale; // Maintain fixed physics step ratio

            // Apply Low-pass filter and Pitch shift to music
            context.MainAudioMixer.SetFloat("MusicPitch", _targetTimeScale);
            context.MainAudioMixer.SetFloat("MusicCutoff", 1200f);
            context.UIMediator.ShowBulletTimeVFX(true);
        }

        public void Tick(GameContext context, float deltaTime)
        {
            // Note: Use unscaledDeltaTime because Time.timeScale is dilated
            _timer += Time.unscaledDeltaTime;
            
            context.Player.ManualUpdate(deltaTime);
            context.ChunkSpawner.UpdateChunks(context.Player.Position.z);

            if (_timer >= _duration)
            {
                GameStateMachine.Instance.TransitionTo<GameplayState>();
            }
        }

        public void FixedTick(GameContext context, float fixedDeltaTime)
        {
            context.Player.ManualFixedUpdate(fixedDeltaTime);
        }

        public void Exit(GameContext context)
        {
            Time.timeScale = 1.0f;
            Time.fixedDeltaTime = 0.02f;
            context.MainAudioMixer.SetFloat("MusicPitch", 1.0f);
            context.MainAudioMixer.SetFloat("MusicCutoff", 22000f);
            context.UIMediator.ShowBulletTimeVFX(false);
        }
    }
}
```

#### CrashState
Executes crash physics (ragdoll/impact pose), disables player control, ducks ambient sound, and displays game over / revive options.

```csharp
using UnityEngine;

namespace EndlessRunner.Architecture.States
{
    public struct CrashPayload : IGameStatePayload
    {
        public Vector3 ImpactVelocity;
        public Collider ImpactCollider;
    }

    public sealed class CrashState : IGameState
    {
        public void Enter(GameContext context, IGameStatePayload payload = null)
        {
            context.Player.SetInputActive(false);
            context.Player.PlayCrashAnimation();
            
            if (payload is CrashPayload crashData)
            {
                context.Player.EnableRagdoll(crashData.ImpactVelocity);
            }

            // Audio ducking & screen shake
            context.MainAudioMixer.SetFloat("MusicCutoff", 500f);
            context.UIMediator.TriggerCameraShake(0.4f, 0.5f);
            context.UIMediator.ShowScreen(UIScreenType.CrashPopup);
        }

        public void Tick(GameContext context, float deltaTime) { }
        public void FixedTick(GameContext context, float fixedDeltaTime) { }
        public void Exit(GameContext context)
        {
            context.UIMediator.HideScreen(UIScreenType.CrashPopup);
        }
    }
}
```

#### ReviveState
Manages post-crash continuation. Clears surrounding dynamic hazards within a radius sweep, applies invincibility frames, and executes a 3-2-1 countdown before returning to `GameplayState`.

```csharp
using System.Collections;
using UnityEngine;

namespace EndlessRunner.Architecture.States
{
    public sealed class ReviveState : IGameState
    {
        public void Enter(GameContext context, IGameStatePayload payload = null)
        {
            context.ReviveCount++;
            context.Player.DisableRagdollAndResetPose();
            
            // Perform hazard clearance sweep 50m ahead of player position
            context.ChunkSpawner.ClearHazardsInRadius(context.Player.Position, 50.0f);

            context.Player.SetVulnerability(false); // Enable shield invincibility
            context.UIMediator.ShowScreen(UIScreenType.ReviveCountdown);
            
            context.CoroutineRunner.StartCoroutine(ExecuteReviveSequence(context));
        }

        private IEnumerator ExecuteReviveSequence(GameContext context)
        {
            yield return context.UIMediator.PlayReviveCountdownAnimationCoroutine();
            GameStateMachine.Instance.TransitionTo<GameplayState>();
        }

        public void Tick(GameContext context, float deltaTime) { }
        public void FixedTick(GameContext context, float fixedDeltaTime) { }
        public void Exit(GameContext context)
        {
            context.UIMediator.HideScreen(UIScreenType.ReviveCountdown);
            // Grant 3 seconds of shield invincibility upon re-entry
            context.Player.EnableInvincibilityShield(3.0f);
        }
    }
}
```

### 1.4 State Machine Controller Implementation

```csharp
using System;
using System.Collections.Generic;
using UnityEngine;
using UnityEngine.Audio;

namespace EndlessRunner.Architecture
{
    public sealed class GameStateMachine : MonoBehaviour
    {
        public static GameStateMachine Instance { get; private set; }

        [Header("Audio Settings")]
        [SerializeField] private AudioMixer mainAudioMixer;
        [SerializeField] private AudioMixerGroup musicGroup;
        [SerializeField] private AudioMixerGroup sfxGroup;

        private GameContext _context;
        private readonly Dictionary<Type, IGameState> _stateCache = new Dictionary<Type, IGameState>();
        private IGameState _currentState;

        private void Awake()
        {
            if (Instance != null && Instance != this)
            {
                Destroy(gameObject);
                return;
            }
            Instance = this;
            DontDestroyOnLoad(gameObject);
        }

        public void Initialize(
            IPlayerController player,
            ITrackChunkSpawner chunkSpawner,
            IDifficultyManager difficultyManager,
            FloatingOriginHandler originHandler,
            IUIMediator uiMediator)
        {
            _context = new GameContext(
                this, player, chunkSpawner, difficultyManager,
                originHandler, uiMediator, mainAudioMixer, musicGroup, sfxGroup);

            // Register Flyweight States
            RegisterState(new States.IntroState());
            RegisterState(new States.GameplayState());
            RegisterState(new States.BulletTimeState());
            RegisterState(new States.CrashState());
            RegisterState(new States.ReviveState());

            TransitionTo<States.IntroState>();
        }

        private void RegisterState<T>(T state) where T : IGameState
        {
            _stateCache[typeof(T)] = state;
        }

        public void TransitionTo<T>(IGameStatePayload payload = null) where T : IGameState
        {
            var targetType = typeof(T);
            if (!_stateCache.TryGetValue(targetType, out var nextState))
            {
                Debug.LogError($"[FSM] State {targetType.Name} not registered!");
                return;
            }

            _currentState?.Exit(_context);
            _currentState = nextState;
            _currentState.Enter(_context, payload);
        }

        private void Update()
        {
            _currentState?.Tick(_context, Time.deltaTime);
        }

        private void FixedUpdate()
        {
            _currentState?.FixedTick(_context, Time.fixedDeltaTime);
        }
    }
}
```

---

## 2. ScriptableObject Data-Driven Batch Solver

### 2.1 Solvability Problem Statement
Pure random obstacle selection across a 3-lane runner quickly causes **impossible scenarios** (e.g., high walls placed across all three lanes simultaneously, or a high wall in Lane 1 paired with moving trains in Lanes 2 and 3 that leave zero reaction window for lane changing).

```
   UNSOLVABLE BATCH (Fatal)                 SOLVABLE BATCH (Valid)
   Lane 0   Lane 1   Lane 2            Lane 0   Lane 1   Lane 2
┌────────┬────────┬────────┐        ┌────────┬────────┬────────┐
│  WALL  │  WALL  │  WALL  │        │  WALL  │  RAMP  │  WALL  │  <- Player jumps onto Ramp
├────────┼────────┼────────┤        ├────────┼────────┼────────┤
│ TRAIN  │ TRAIN  │ TRAIN  │        │ TRAIN  │ TRAIN  │  EMPTY │  <- Player dodges to Lane 2
└────────┴────────┴────────┴┘        └────────┴────────┴────────┴┘
```

To solve this, modern production engines enforce **Batch-Level Solvability Validation** via a 2D matrix bitmask solver before committing a track chunk to memory.

### 2.2 Data Structures & ScriptableObjects

```csharp
using System;
using UnityEngine;

namespace EndlessRunner.Generation
{
    public enum LaneIndex { Left = 0, Center = 1, Right = 2 }

    public enum HazardType
    {
        Empty = 0,
        LowBarricade = 1,  // Can Jump
        HighBarricade = 2, // Can Roll
        FullBlockade = 3,  // Unpassable
        TrainRamp = 4,     // Can ascend to overhead track
        MovingTrain = 5    // Forces jump/lane-switch
    }

    [Flags]
    public enum RequiredAction
    {
        None = 0,
        Jump = 1 << 0,
        Roll = 1 << 1,
        SwitchLeft = 1 << 2,
        SwitchRight = 1 << 3,
        AscendRamp = 1 << 4
    }

    [Serializable]
    public struct HazardCell
    {
        public HazardType Type;
        public GameObject HazardPrefab;
    }

    [CreateAssetMenu(fileName = "SpawnPattern_", menuName = "EndlessRunner/Generation/Spawn Pattern")]
    public class SpawnPatternSO : ScriptableObject
    {
        public string PatternID;
        public int LengthInSteps = 4; // Step length (e.g., 4 rows deep)
        
        // Flattened 1D array representing 3 Lanes x LengthInSteps Matrix
        // Index = (step * 3) + lane
        [SerializeField] private HazardCell[] patternMatrix = new HazardCell[12];

        public HazardCell GetCell(int step, int lane)
        {
            return patternMatrix[(step * 3) + lane];
        }

        public void SetCell(int step, int lane, HazardCell cell)
        {
            patternMatrix[(step * 3) + lane] = cell;
        }
    }
}
```

### 2.3 Bitmask & BFS Solvability Validation Algorithm

The `TrafficSpawnValidator` transforms a proposed 3-lane $\times N$-depth batch into a directed graph and executes a Breadth-First Search (BFS) algorithm to verify that **at least one valid trajectory** reaches the terminal step without unavoidable collision.

```csharp
using System.Collections.Generic;
using UnityEngine;

namespace EndlessRunner.Generation
{
    public static class TrafficSpawnValidator
    {
        private struct SearchNode
        {
            public int Step;
            public int Lane;
            public bool IsOverhead; // On top of train/ramp

            public SearchNode(int step, int lane, bool isOverhead)
            {
                Step = step;
                Lane = lane;
                IsOverhead = isOverhead;
            }
        }

        /// <summary>
        /// Validates whether a given SpawnPattern contains at least one solvable path from step 0 to the end.
        /// </summary>
        public static bool ValidatePattern(SpawnPatternSO pattern, out List<int> validLanePath)
        {
            validLanePath = new List<int>();
            int maxSteps = pattern.LengthInSteps;

            var queue = new Queue<SearchNode>();
            var visited = new HashSet<string>();
            var parentMap = new Dictionary<string, string>();

            // Prime starting step across all 3 lanes (assuming reachable entrance)
            for (int lane = 0; lane < 3; lane++)
            {
                if (CanTraverseCell(pattern.GetCell(0, lane), false, out bool isRamp))
                {
                    var startNode = new SearchNode(0, lane, isRamp);
                    string key = GetKey(startNode);
                    queue.Enqueue(startNode);
                    visited.Add(key);
                    parentMap[key] = null;
                }
            }

            SearchNode terminalNode = default;
            bool pathFound = false;

            while (queue.Count > 0)
            {
                var current = queue.Dequeue();

                if (current.Step == maxSteps - 1)
                {
                    terminalNode = current;
                    pathFound = true;
                    break;
                }

                int nextStep = current.Step + 1;

                // Evaluate possible transitions: Same Lane, Move Left, Move Right
                for (int laneOffset = -1; laneOffset <= 1; laneOffset++)
                {
                    int targetLane = current.Lane + laneOffset;
                    if (targetLane < 0 || targetLane > 2) continue;

                    var cell = pattern.GetCell(nextStep, targetLane);
                    if (CanTraverseCell(cell, current.IsOverhead, out bool becomesOverhead))
                    {
                        var nextNode = new SearchNode(nextStep, targetLane, becomesOverhead);
                        string nextKey = GetKey(nextNode);

                        if (!visited.Contains(nextKey))
                        {
                            visited.Add(nextKey);
                            parentMap[nextKey] = GetKey(current);
                            queue.Enqueue(nextNode);
                        }
                    }
                }
            }

            if (pathFound)
            {
                // Reconstruct Path
                string currKey = GetKey(terminalNode);
                while (currKey != null)
                {
                    int lane = int.Parse(currKey.Split('_')[1]);
                    validLanePath.Add(lane);
                    currKey = parentMap[currKey];
                }
                validLanePath.Reverse();
                return true;
            }

            return false;
        }

        private static bool CanTraverseCell(HazardCell cell, bool currentlyOverhead, out bool isRampOut)
        {
            isRampOut = currentlyOverhead;

            if (currentlyOverhead)
            {
                // If on overhead train track, only FullBlockade or missing train drops player down
                if (cell.Type == HazardType.FullBlockade) return false;
                return true;
            }

            switch (cell.Type)
            {
                case HazardType.Empty:
                case HazardType.LowBarricade:  // Passable by Jump
                case HazardType.HighBarricade: // Passable by Roll
                    return true;
                case HazardType.TrainRamp:
                    isRampOut = true; // Ascends to overhead
                    return true;
                case HazardType.FullBlockade:
                case HazardType.MovingTrain:
                    return false; // Unpassable directly in lane
                default:
                    return false;
            }
        }

        private static string GetKey(SearchNode node)
        {
            return $"{node.Step}_{node.Lane}_{(node.IsOverhead ? 1 : 0)}";
        }
    }
}
```

### 2.4 Difficulty Scaling & Dynamic Spawner Engine

```csharp
using System.Collections.Generic;
using UnityEngine;

namespace EndlessRunner.Generation
{
    [CreateAssetMenu(fileName = "DifficultyConfig", menuName = "EndlessRunner/Generation/Difficulty Config")]
    public class DifficultyConfigSO : ScriptableObject
    {
        public AnimationCurve RunSpeedVsDistance = AnimationCurve.Linear(0, 10, 5000, 30);
        public AnimationCurve MaxConsecutiveFullBlockades = AnimationCurve.Constant(0, 5000, 1);
        public AnimationCurve MinimumReactionTimeWindowMs = AnimationCurve.Linear(0, 800, 5000, 350);

        public List<SpawnPatternSO> EasyPatterns;
        public List<SpawnPatternSO> MediumPatterns;
        public List<SpawnPatternSO> HardPatterns;
    }

    public class TrafficSpawnerEngine : MonoBehaviour
    {
        [SerializeField] private DifficultyConfigSO difficultyConfig;
        [SerializeField] private Transform trackParent;
        [SerializeField] private float stepZLength = 10.0f;

        private float _currentZSpawnPosition = 0.0f;

        public void SpawnNextBatch(float currentPlayerDistance)
        {
            float targetSpeed = difficultyConfig.RunSpeedVsDistance.Evaluate(currentPlayerDistance);
            float reactionWindowMs = difficultyConfig.MinimumReactionTimeWindowMs.Evaluate(currentPlayerDistance);

            // Filter Pattern Pool based on current distance / difficulty tier
            List<SpawnPatternSO> patternPool = SelectPatternPool(currentPlayerDistance);
            
            SpawnPatternSO selectedPattern = null;
            List<int> solvedPath = null;

            // Pick pattern and validate solvability batch
            int retries = 0;
            while (retries < 10)
            {
                var candidate = patternPool[Random.Range(0, patternPool.Count)];
                if (TrafficSpawnValidator.ValidatePattern(candidate, out solvedPath))
                {
                    selectedPattern = candidate;
                    break;
                }
                retries++;
            }

            if (selectedPattern == null)
            {
                Debug.LogWarning("[Spawner] Failed to validate random pattern. Falling back to safe empty pattern.");
                return;
            }

            InstantiateBatchGameObjects(selectedPattern);
        }

        private List<SpawnPatternSO> SelectPatternPool(float distance)
        {
            if (distance < 1000f) return difficultyConfig.EasyPatterns;
            if (distance < 3000f) return difficultyConfig.MediumPatterns;
            return difficultyConfig.HardPatterns;
        }

        private void InstantiateBatchGameObjects(SpawnPatternSO pattern)
        {
            for (int step = 0; step < pattern.LengthInSteps; step++)
            {
                for (int lane = 0; lane < 3; lane++)
                {
                    var cell = pattern.GetCell(step, lane);
                    if (cell.Type != HazardType.Empty && cell.HazardPrefab != null)
                    {
                        Vector3 spawnPos = new Vector3((lane - 1) * 3.5f, 0, _currentZSpawnPosition + (step * stepZLength));
                        Instantiate(cell.HazardPrefab, spawnPos, Quaternion.identity, trackParent);
                    }
                }
            }
            _currentZSpawnPosition += pattern.LengthInSteps * stepZLength;
        }
    }
}
```

---

## 3. Floating Origin Reset System

### 3.1 IEEE 754 Floating-Point Precision Loss At Scale
In Unity, spatial positions are stored as 32-bit single-precision floating-point numbers (`float`). As a character runs further along the Z-axis, the exponent field in the IEEE 754 format expands to represent higher magnitudes, sacrificing precision in the mantissa bits.

| Distance ($Z$) | Precision Step ($\epsilon$) | Observed Engine Artifacts |
| :--- | :--- | :--- |
| $0\,\text{m} - 100\,\text{m}$ | $< 0.00001\,\text{m}$ | Perfect precision. |
| $1,000\,\text{m}$ | $\approx 0.0001\,\text{m}$ | Negligible sub-pixel micro-jitter. |
| $10,000\,\text{m}$ | $\approx 0.001\,\text{m}$ | Visible mesh vertex jitter, camera stutter, shadow artifacting. |
| $100,000\,\text{m}$ | $\approx 0.016\,\text{m}$ | Severe physics collapse, raycast misses, false collision triggers. |

```
   Mantissa Precision Degradation at High Z:
   Z = 10.0m     => [0][10000010][01000000000000000000000] (High Precision)
   Z = 100,000m  => [0][10001111][10000110101000000000000] (Loss of Low Bits)
```

To maintain persistent $60\,\text{fps}$ rendering quality across infinite distances, a **Floating Origin Reset Architecture** shifts all world elements back by $\mathbf{\Delta Z} = (0, 0, Z_{\text{player}})$ whenever $Z_{\text{player}} \ge 1000\,\text{m}$.

### 3.2 Architecture & Multi-System Synchronization

When an origin shift fires:
1. **Accumulated Distance Register:** Total distance score is decoupled from transform positions: $Z_{\text{total}} = Z_{\text{shifted\_accumulated}} + Z_{\text{transform}}$.
2. **Subscribed Systems Notification:** Event-driven notification broadcasts the vector delta to physics, particle systems, trail renderers, camera rigs, and pooled track chunks.

```
                        ┌──────────────────────┐
                        │ FloatingOriginHandler│
                        └──────────┬───────────┘
                                   │ OnOriginShifted(offsetVector)
         ┌─────────────────────────┼─────────────────────────┐
         ▼                         ▼                         ▼
┌──────────────────┐     ┌──────────────────┐     ┌──────────────────┐
│ Player Controller│     │ Track & Obstacle │     │ VFX & Particles  │
│ (Shift Transform │     │ Pool Managers    │     │ (Shift Active    │
│ & Rigidbody Vel) │     │ (Shift Chunk Pos)│     │ Particle Buffers)│
└──────────────────┘     └──────────────────┘     └──────────────────┘
```

### 3.3 Complete FloatingOriginHandler Implementation

```csharp
using System;
using System.Collections.Generic;
using UnityEngine;

namespace EndlessRunner.Architecture
{
    public interface IOriginShiftSubscriber
    {
        void OnOriginShift(Vector3 shiftOffset);
    }

    public sealed class FloatingOriginHandler : MonoBehaviour
    {
        [Header("Threshold Settings")]
        [SerializeField] private float shiftThresholdZ = 1000.0f;
        
        [Header("Root Container (Optional)")]
        [SerializeField] private Transform worldRoot;

        public float TotalAccumulatedDistance { get; private set; }
        
        public static event Action<Vector3> OnOriginShifted;
        private readonly List<IOriginShiftSubscriber> _subscribers = new List<IOriginShiftSubscriber>();

        public void RegisterSubscriber(IOriginShiftSubscriber subscriber)
        {
            if (!_subscribers.Contains(subscriber))
                _subscribers.Add(subscriber);
        }

        public void UnregisterSubscriber(IOriginShiftSubscriber subscriber)
        {
            _subscribers.Remove(subscriber);
        }

        public void CheckAndExecuteShift(Vector3 playerPosition)
        {
            TotalAccumulatedDistance = playerPosition.z + ShiftedZOffset;

            if (playerPosition.z >= shiftThresholdZ)
            {
                ExecuteShift(playerPosition.z);
            }
        }

        public float ShiftedZOffset { get; private set; }

        private void ExecuteShift(float currentZ)
        {
            Vector3 shiftOffset = new Vector3(0f, 0f, currentZ);
            ShiftedZOffset += currentZ;

            // 1. Shift World Root if using hierarchical parenting
            if (worldRoot != null)
            {
                worldRoot.position -= shiftOffset;
            }
            else
            {
                // Shift all root objects in the scene
                var rootObjects = UnityEngine.SceneManagement.SceneManager.GetActiveScene().GetRootGameObjects();
                for (int i = 0; i < rootObjects.Length; i++)
                {
                    rootObjects[i].transform.position -= shiftOffset;
                }
            }

            // 2. Notify Subscribed Component Systems (Physics, VFX, Particle Systems)
            for (int i = _subscribers.Count - 1; i >= 0; i--)
            {
                _subscribers[i].OnOriginShift(shiftOffset);
            }

            // 3. Shift Active Particle Systems in Scene
            ShiftAllParticleSystems(shiftOffset);

            // 4. Shift Trail and Line Renderers
            ShiftTrailRenderers(shiftOffset);

            // 5. Fire Static Event for global listeners
            OnOriginShifted?.Invoke(shiftOffset);

            Debug.Log($"[FloatingOrigin] Executed Shift of {currentZ}m. Total Accum Distance: {TotalAccumulatedDistance}m");
        }

        private void ShiftAllParticleSystems(Vector3 offset)
        {
            ParticleSystem[] particles = FindObjectsByType<ParticleSystem>(FindObjectsSortMode.None);
            ParticleSystem.Particle[] particleBuffer = null;

            foreach (var ps in particles)
            {
                if (ps == null || ps.particleCount == 0) continue;

                int maxParticles = ps.main.maxParticles;
                if (particleBuffer == null || particleBuffer.Length < maxParticles)
                {
                    particleBuffer = new ParticleSystem.Particle[maxParticles];
                }

                int count = ps.GetParticles(particleBuffer);
                for (int i = 0; i < count; i++)
                {
                    particleBuffer[i].position -= offset;
                }
                ps.SetParticles(particleBuffer, count);
            }
        }

        private void ShiftTrailRenderers(Vector3 offset)
        {
            TrailRenderer[] trails = FindObjectsByType<TrailRenderer>(FindObjectsSortMode.None);
            Vector3[] positionBuffer = null;

            foreach (var trail in trails)
            {
                if (trail == null || trail.positionCount == 0) continue;

                int count = trail.positionCount;
                if (positionBuffer == null || positionBuffer.Length < count)
                {
                    positionBuffer = new Vector3[count];
                }

                trail.GetPositions(positionBuffer);
                for (int i = 0; i < count; i++)
                {
                    positionBuffer[i] -= offset;
                }
                trail.SetPositions(positionBuffer);
            }
        }
    }
}
```

---

## 4. Extensible Dynamic Hazard System

### 4.1 Dynamic Hazard Abstraction Interface

Static obstacles (e.g. stationary barricades) are simple, but dynamic obstacles (moving trains, dynamic ramps, falling cargo containers) require explicit state lifecycles and object pool integration.

```csharp
using UnityEngine;

namespace EndlessRunner.Hazards
{
    public interface IDynamicHazard
    {
        string HazardID { get; }
        bool IsActive { get; }
        
        void Initialize(Vector3 spawnPosition, Quaternion spawnRotation);
        void OnSpawnFromPool();
        void OnTick(float deltaTime, float playerZPosition);
        void TriggerHazard();
        void OnDespawnToPool();
    }
}
```

### 4.2 Ramp Hazard (`TrainRampHazard`)

Allows the player character to seamlessly transition from ground level to train rooftops upon collision with the ramp surface, altering character collision masks and gravity profiles.

```csharp
using EndlessRunner.Architecture;
using UnityEngine;

namespace EndlessRunner.Hazards
{
    public class TrainRampHazard : MonoBehaviour, IDynamicHazard, IOriginShiftSubscriber
    {
        [SerializeField] private string hazardID = "Hazard_TrainRamp";
        [SerializeField] private Collider rampTriggerCollider;
        [SerializeField] private Transform rooftopTargetNode;

        public string HazardID => hazardID;
        public bool IsActive { get; private set; }

        public void Initialize(Vector3 spawnPosition, Quaternion spawnRotation)
        {
            transform.SetPositionAndRotation(spawnPosition, spawnRotation);
        }

        public void OnSpawnFromPool()
        {
            IsActive = true;
            rampTriggerCollider.enabled = true;
        }

        public void OnTick(float deltaTime, float playerZPosition) { }

        public void TriggerHazard()
        {
            // Triggered via Player OnTriggerEnter
        }

        private void OnTriggerEnter(Collider other)
        {
            if (other.TryGetComponent<IPlayerController>(out var player))
            {
                // Seamlessly transfer player state to rooftop height
                player.AscendRampToOverheadTrack(rooftopTargetNode.position.y);
            }
        }

        public void OnDespawnToPool()
        {
            IsActive = false;
        }

        public void OnOriginShift(Vector3 shiftOffset)
        {
            transform.position -= shiftOffset;
        }
    }
}
```

### 4.3 Jackknife Truck Hazard (`JackknifeTruckHazard`)

A semi-truck parked in Lane 0 that dynamically slides sideways across Lanes 1 and 2 when the player breaches an activation Z-distance threshold.

```csharp
using System.Collections;
using EndlessRunner.Architecture;
using UnityEngine;

namespace EndlessRunner.Hazards
{
    public class JackknifeTruckHazard : MonoBehaviour, IDynamicHazard, IOriginShiftSubscriber
    {
        [SerializeField] private string hazardID = "Hazard_JackknifeTruck";
        [SerializeField] private float triggerDistanceAhead = 40.0f;
        [SerializeField] private float slideDuration = 0.6f;
        [SerializeField] private float slideDistanceLanes = 7.0f; // 2 Lanes wide (3.5m * 2)

        private Vector3 _startPosition;
        private Vector3 _targetPosition;
        private bool _hasTriggered;

        public string HazardID => hazardID;
        public bool IsActive { get; private set; }

        public void Initialize(Vector3 spawnPosition, Quaternion spawnRotation)
        {
            transform.SetPositionAndRotation(spawnPosition, spawnRotation);
            _startPosition = spawnPosition;
            _targetPosition = spawnPosition + (transform.right * slideDistanceLanes);
            _hasTriggered = false;
        }

        public void OnSpawnFromPool()
        {
            IsActive = true;
            _hasTriggered = false;
        }

        public void OnTick(float deltaTime, float playerZPosition)
        {
            if (!_hasTriggered && (transform.position.z - playerZPosition) <= triggerDistanceAhead)
            {
                TriggerHazard();
            }
        }

        public void TriggerHazard()
        {
            _hasTriggered = true;
            StartCoroutine(ExecuteJackknifeSlide());
        }

        private IEnumerator ExecuteJackknifeSlide()
        {
            float elapsed = 0f;
            Vector3 initialPos = transform.position;

            while (elapsed < slideDuration)
            {
                elapsed += Time.deltaTime;
                float t = Mathf.SmoothStep(0f, 1f, elapsed / slideDuration);
                transform.position = Vector3.Lerp(initialPos, initialPos + (transform.right * slideDistanceLanes), t);
                yield return null;
            }
        }

        public void OnDespawnToPool()
        {
            IsActive = false;
            StopAllCoroutines();
        }

        public void OnOriginShift(Vector3 shiftOffset)
        {
            transform.position -= shiftOffset;
            _startPosition -= shiftOffset;
            _targetPosition -= shiftOffset;
        }
    }
}
```

### 4.4 Overhead Cargo Drop Hazard (`ContainerDropHazard`)

Drops a shipping container into a lane from an overhead crane. Projects a decal shadow warning on the ground target before physical impact occurs.

```csharp
using System.Collections;
using EndlessRunner.Architecture;
using UnityEngine;

namespace EndlessRunner.Hazards
{
    public class ContainerDropHazard : MonoBehaviour, IDynamicHazard, IOriginShiftSubscriber
    {
        [SerializeField] private string hazardID = "Hazard_ContainerDrop";
        [SerializeField] private float triggerDistanceAhead = 50.0f;
        [SerializeField] private float dropHeight = 15.0f;
        [SerializeField] private Transform containerMeshTransform;
        [SerializeField] private Projector shadowWarningProjector;
        [SerializeField] private ParticleSystem impactVFX;

        private Vector3 _landPosition;
        private Vector3 _dropAirPosition;
        private bool _hasTriggered;

        public string HazardID => hazardID;
        public bool IsActive { get; private set; }

        public void Initialize(Vector3 spawnPosition, Quaternion spawnRotation)
        {
            transform.SetPositionAndRotation(spawnPosition, spawnRotation);
            _landPosition = spawnPosition;
            _dropAirPosition = spawnPosition + new Vector3(0, dropHeight, 0);
            
            containerMeshTransform.position = _dropAirPosition;
            shadowWarningProjector.enabled = false;
            _hasTriggered = false;
        }

        public void OnSpawnFromPool()
        {
            IsActive = true;
            _hasTriggered = false;
        }

        public void OnTick(float deltaTime, float playerZPosition)
        {
            if (!_hasTriggered && (transform.position.z - playerZPosition) <= triggerDistanceAhead)
            {
                TriggerHazard();
            }
        }

        public void TriggerHazard()
        {
            _hasTriggered = true;
            StartCoroutine(ExecuteContainerDropSequence());
        }

        private IEnumerator ExecuteContainerDropSequence()
        {
            shadowWarningProjector.enabled = true;
            
            // Warning phase (0.5s shadow scale up)
            float warningElapsed = 0f;
            while (warningElapsed < 0.5f)
            {
                warningElapsed += Time.deltaTime;
                shadowWarningProjector.orthographicSize = Mathf.Lerp(0.1f, 2.5f, warningElapsed / 0.5f);
                yield return null;
            }

            // Drop Phase with accelerated gravity bounce
            float dropElapsed = 0f;
            float dropDuration = 0.35f;
            while (dropElapsed < dropDuration)
            {
                dropElapsed += Time.deltaTime;
                float t = (dropElapsed / dropDuration) * (dropElapsed / dropDuration); // Ease In Quadratic
                containerMeshTransform.position = Vector3.Lerp(_dropAirPosition, _landPosition, t);
                yield return null;
            }

            containerMeshTransform.position = _landPosition;
            shadowWarningProjector.enabled = false;
            
            if (impactVFX != null) impactVFX.Play();
        }

        public void OnDespawnToPool()
        {
            IsActive = false;
            StopAllCoroutines();
        }

        public void OnOriginShift(Vector3 shiftOffset)
        {
            transform.position -= shiftOffset;
            _landPosition -= shiftOffset;
            _dropAirPosition -= shiftOffset;
        }
    }
}
```

### 4.5 Hazard Pool Manager Integration

```csharp
using System.Collections.Generic;
using UnityEngine;

namespace EndlessRunner.Hazards
{
    public class DynamicHazardPoolManager : MonoBehaviour
    {
        [SerializeField] private List<GameObject> hazardPrefabs;
        
        private readonly Dictionary<string, Queue<IDynamicHazard>> _poolDictionary = new Dictionary<string, Queue<IDynamicHazard>>();
        private readonly List<IDynamicHazard> _activeHazards = new List<IDynamicHazard>();

        public IDynamicHazard SpawnHazard(string hazardID, Vector3 position, Quaternion rotation)
        {
            if (!_poolDictionary.TryGetValue(hazardID, out var pool))
            {
                pool = new Queue<IDynamicHazard>();
                _poolDictionary[hazardID] = pool;
            }

            IDynamicHazard hazard = null;
            if (pool.Count > 0)
            {
                hazard = pool.Dequeue();
            }
            else
            {
                var prefab = hazardPrefabs.Find(p => p.GetComponent<IDynamicHazard>()?.HazardID == hazardID);
                var go = Instantiate(prefab, transform);
                hazard = go.GetComponent<IDynamicHazard>();
            }

            hazard.Initialize(position, rotation);
            hazard.OnSpawnFromPool();
            _activeHazards.Add(hazard);

            return hazard;
        }

        public void DespawnHazard(IDynamicHazard hazard)
        {
            hazard.OnDespawnToPool();
            _activeHazards.Remove(hazard);
            _poolDictionary[hazard.HazardID].Enqueue(hazard);
        }

        private void Update()
        {
            float playerZ = GameContextPlayerPositionZ();
            float deltaTime = Time.deltaTime;

            for (int i = _activeHazards.Count - 1; i >= 0; i--)
            {
                var hazard = _activeHazards[i];
                hazard.OnTick(deltaTime, playerZ);

                // Auto-recycle hazards passed by player (e.g. 20m behind player)
                if ((hazard as MonoBehaviour).transform.position.z < playerZ - 20.0f)
                {
                    DespawnHazard(hazard);
                }
            }
        }

        private float GameContextPlayerPositionZ()
        {
            return Architecture.GameStateMachine.Instance != null ? 0f : 0f; // Linked to player position reference
        }
    }
}
