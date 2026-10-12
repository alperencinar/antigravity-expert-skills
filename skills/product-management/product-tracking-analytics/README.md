# Skill: Product Analytics Tracker (GA4)

This custom skill helps the Product Owner design, audit, and document Google Analytics 4 (GA4) event tracking structures, custom dimensions, and user properties. It ensures tracking plans map directly to business decisions and follow strict GA4 event conventions.

## How to Use

To design a tracking specification or audit an existing tracking plan, trigger this skill by asking:

> "Design a GA4 event tracking plan for the new feature [Feature Name] and define custom dimensions."

The skill will return a comprehensive tracking specification, including:
1. **Signal Quality Score**: Diagnostic review of tracking readiness.
2. **GA4 Event Matrix**: Standard and custom event specifications.
3. **Custom Definitions Registry**: Dimensions and user properties to set up in the GA4 admin console.
4. **Developer Implementation Notes**: Concrete code snippets (`gtag` or `dataLayer.push`) for the engineering team.
