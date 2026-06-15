"""Add jwt_required to AI writing endpoints"""
with open('src/api/v2/advanced_features/ai_recommendations.py', encoding='utf-8') as f:
    content = f.read()

replacements = [
    ('@router.post("/writing/continue")\n@_catch\nasync def smart_continue(request: TextRequest):',
     '@router.post("/writing/continue")\n@_catch\nasync def smart_continue(request: TextRequest, current_user=Depends(jwt_required)):'),
    ('@router.post("/writing/transform-style")\n@_catch\nasync def transform_style(request: TextRequest):',
     '@router.post("/writing/transform-style")\n@_catch\nasync def transform_style(request: TextRequest, current_user=Depends(jwt_required)):'),
    ('@router.post("/writing/check-grammar")\n@_catch\nasync def check_grammar(request: TextGrammarRequest):',
     '@router.post("/writing/check-grammar")\n@_catch\nasync def check_grammar(request: TextGrammarRequest, current_user=Depends(jwt_required)):'),
    ('@router.post("/writing/polish")\n@_catch\nasync def polish_text(request: TextPolishRequest):',
     '@router.post("/writing/polish")\n@_catch\nasync def polish_text(request: TextPolishRequest, current_user=Depends(jwt_required)):'),
    ('@router.post("/writing/generate-titles")\n@_catch\nasync def generate_titles(',
     '@router.post("/writing/generate-titles")\n@_catch\nasync def generate_titles(current_user=Depends(jwt_required), '),
]

for old, new in replacements:
    if old in content:
        content = content.replace(old, new)
        print(f"  Replaced: {old.split(chr(10))[0]}")
    else:
        print(f"  NOT FOUND: {old.split(chr(10))[0]}")

with open('src/api/v2/advanced_features/ai_recommendations.py', 'w', encoding='utf-8') as f:
    f.write(content)
print("Done")
