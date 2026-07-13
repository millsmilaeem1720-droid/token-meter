from token_meter import call_chat, sts 
text, info = call_chat("用一句话解释RAG", api_key="sk-2a3422d12dfc4973beea6635a6a5cf78") 
print(f"回复: {text}\n成本: ${info['cost']}") 
print(sts()) 
