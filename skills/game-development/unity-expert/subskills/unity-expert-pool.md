# /unity-expert-pool - Zero-GC Object Pooling & Dynamic Event System

Runtime heap allocation'ı sıfırlar ve dinamik kinetik çevresel tehlikeleri yönetir.

## Pooling & Event Kuralları

1. **Zero-GC Sözleşmeleri**: `IPoolable` (`OnSpawn`, `OnDespawn`) implemente et; prefab init sırasında `IPoolable[]` ve `Rigidbody[]` dizilerini pre-cache'le.
2. **Payload Decoupling Kuralı**: Kamyon yükü düştüğünde (örn. `FallingContainerEvent`) child mesh'i ASLA unparent etme; child mesh'i `SetActive(false)` ile gizle ve yola ayrı pooled `FallenContainer` engel prefabı spawn et.
3. **Component Churn Yasağı**: Gameplay spawn sırasında asla `DestroyImmediate` veya `AddComponent` çağırma.
4. **Time.timeScale Fizik Senkronu**: Slow-motion sırasında daima `Time.fixedDeltaTime = 0.02f * Time.timeScale` güncelle.

## Referans Dokümanlar
- [`mobile_performance_zero_gc_architecture.md`](../researches/mobile_performance_zero_gc_architecture.md)
- [`object_pooling_and_dynamic_events.md`](../researches/object_pooling_and_dynamic_events.md)
