import os
import re
import yaml

# Resolve relative to the script location: skills/product-management/product-orchestrating/scripts/
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SKILLS_DIR = os.path.normpath(os.path.join(SCRIPT_DIR, "../../.."))

def discover_skills(skills_root):
    skills = []
    for item in sorted(os.listdir(skills_root)):
        item_path = os.path.join(skills_root, item)
        if not os.path.isdir(item_path) or item.startswith("."):
            continue
        if os.path.exists(os.path.join(item_path, "SKILL.md")):
            skills.append((item, item_path, None))
        else:
            for sub in sorted(os.listdir(item_path)):
                sub_path = os.path.join(item_path, sub)
                if os.path.isdir(sub_path) and os.path.exists(os.path.join(sub_path, "SKILL.md")):
                    skills.append((sub, sub_path, item))
    return skills

def check_skill(skill_dir, skill_name):
    skill_path = os.path.join(skill_dir, "SKILL.md")
    if not os.path.exists(skill_path):
        return f"File does not exist: {skill_path}"
    
    with open(skill_path, "r", encoding="utf-8") as f:
        content = f.read()
        
    lines = content.splitlines()
    line_count = len(lines)
    
    # Parse YAML frontmatter
    frontmatter_match = re.match(r"^---\s*\n(.*?)\n---\s*\n", content, re.DOTALL)
    if not frontmatter_match:
        return "Missing or malformed YAML frontmatter"
        
    yaml_content = frontmatter_match.group(1)
    try:
        data = yaml.safe_load(yaml_content)
    except Exception as e:
        return f"Invalid YAML frontmatter: {e}"
        
    errors = []
    if "name" not in data:
        errors.append("Missing 'name' in frontmatter")
    elif data["name"] != skill_name:
        errors.append(f"Name mismatch in frontmatter: found '{data['name']}', expected '{skill_name}'")
        
    if "description" not in data:
        errors.append("Missing 'description' in frontmatter")
    else:
        desc = data["description"]
        if len(desc) > 1024:
            errors.append(f"Description too long: {len(desc)} chars (max 1024)")
        if not (desc.startswith("Use ") or desc.startswith("This skill") or desc.startswith("Add ") or desc.startswith("Document ") or desc.startswith("Complete ") or desc.startswith("Master ") or desc.startswith("Comprehensive ")):
            errors.append(f"Description might not be in standard third-person/imperative format: '{desc[:30]}...'")
            
    if "description" in data:
        desc_lower = data["description"].lower()
        if "you " in desc_lower or "your " in desc_lower:
            errors.append("Description contains second-person pronouns ('you'/'your')")

    if line_count > 500:
        errors.append(f"Line count too high: {line_count} (max 500)")
        
    # Check relative links to other skills
    links = re.findall(r"\[.*?\]\((.*?)\)", content)
    for link in links:
        if link.startswith("../") or link.startswith("./"):
            target_path = os.path.normpath(os.path.join(skill_dir, link))
            if not os.path.exists(target_path):
                errors.append(f"Broken relative link: '{link}' -> resolved to non-existent '{target_path}'")
                
    return errors

if __name__ == "__main__":
    if not os.path.exists(SKILLS_DIR):
        print(f"Skills directory does not exist: {SKILLS_DIR}")
        exit(1)
        
    skills = discover_skills(SKILLS_DIR)
    
    print(f"Auditing {len(skills)} skills in {SKILLS_DIR} across categories...\n")
    all_ok = True
    for skill_name, skill_path, category in sorted(skills, key=lambda s: (s[2] or '', s[0])):
        cat_prefix = f"[{category}] " if category else ""
        res = check_skill(skill_path, skill_name)
        if isinstance(res, list) and len(res) > 0:
            print(f"❌ {cat_prefix}{skill_name}:")
            for err in res:
                print(f"   - {err}")
            all_ok = False
        elif isinstance(res, str):
            print(f"❌ {cat_prefix}{skill_name}: {res}")
            all_ok = False
        else:
            print(f"✅ {cat_prefix}{skill_name}: Perfect!")
            
    if all_ok:
        print("\nAll skills passed verification successfully!")
