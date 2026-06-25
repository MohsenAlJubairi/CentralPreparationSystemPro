import os

template_dir = 'templates'
for root, dirs, files in os.walk(template_dir):
    for file in files:
        if file.endswith('.html'):
            filepath = os.path.join(root, file)
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Perform replacements
            content = content.replace('bg-blue-', 'bg-primary-')
            content = content.replace('text-blue-', 'text-primary-')
            content = content.replace('border-blue-', 'border-primary-')
            content = content.replace('shadow-blue-', 'shadow-primary-')
            content = content.replace('bg-cyan-', 'bg-amber-')
            content = content.replace('text-cyan-', 'text-amber-')
            content = content.replace('border-cyan-', 'border-amber-')
            content = content.replace('shadow-cyan-', 'shadow-amber-')
            
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
                
print("Color replacement done safely with UTF-8 encoding.")
