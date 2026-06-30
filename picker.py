import json
import argparse

def pick_questions(filepath, n):
    # Load the data
    with open(filepath, 'r') as f:
        data = json.load(f)

    # 1) Add used: false field to every entry if missing
    for q in data:
        if 'used' not in q:
            q['used'] = False

    # 2) Group unused questions by subcategory
    unused_by_sub = {}
    for q in data:
        if not q['used']:
            sub = q.get('subcategory', 'unknown')
            if sub not in unused_by_sub:
                unused_by_sub[sub] = []
            unused_by_sub[sub].append(q)

    subcategories = list(unused_by_sub.keys())
    subcategories.sort()

    picked = []

    # 3) Select the next N unused questions while rotating across subcategories
    if not subcategories:
        print("No unused questions available.")
        return []

    cat_idx = 0
    for _ in range(n):
        if not subcategories:
            print(f"Ran out of unused questions after picking {len(picked)}.")
            break
            
        current_cat = subcategories[cat_idx]
        
        # Pop the first available question in the current subcategory
        q = unused_by_sub[current_cat].pop(0)
        q['used'] = True
        picked.append(q)
        
        # If this category is now empty, remove it from the rotation
        if not unused_by_sub[current_cat]:
            subcategories.pop(cat_idx)
            # Adjust index if we removed the last item in the list
            if len(subcategories) > 0:
                cat_idx = cat_idx % len(subcategories)
        else:
            cat_idx = (cat_idx + 1) % len(subcategories)

    # 4) Save the file back with the updated 'used' flags
    with open(filepath, 'w') as f:
        json.dump(data, f, indent=2)

    print(f"Successfully picked {len(picked)} questions.")
    for p in picked:
        print(f" - [{p.get('subcategory', 'unknown')}] {p['id']}: {p['question']}")

    return picked

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Pick unused questions.')
    parser.add_argument('--n', type=int, default=10, help='Number of questions to pick')
    parser.add_argument('--file', type=str, default='verbal_mcqs.json', help='Path to JSON file')
    args = parser.parse_args()
    
    pick_questions(args.file, args.n)
