# API Documentation
This document provides a detailed summary of the available API endpoints, including explanations, a complete list of supported parameters, and `curl` examples.

Note: Replace your_api_key with your actual API key and MODEL_NAME with the name of the model you want to use.

## 1. V1 API Endpoints
Base path: /v1

### 1.1. POST /chat/completions
Handles chat completions. This endpoint takes a list of messages and returns a generated response.

```
curl -X POST https://api.arliai.com/v1/chat/completions \
-H "Content-Type: application/json" \
-H "Authorization: Bearer your_api_key" \
-d '{
  "model": "MODEL_NAME",
  "messages": [
    {"role": "system", "content": "You are a helpful assistant."},
    {"role": "user", "content": "Hello!"}
  ]
}'
```

### 1.2. POST /chat/completions (with Image)
This endpoint allows you to send a text prompt along with an image for Vision Language Models (VLM). The user message content should be an array containing both the text and the image URL (base64 encoded).

```
curl -X POST https://api.arliai.com/v1/chat/completions \
-H "Content-Type: application/json" \
-H "Authorization: Bearer your_api_key" \
-d '{
 "model": "VLM_MODEL_NAME",
 "messages": [
   {
     "role": "user",
     "content": [
       {"type": "text", "text": "What is in this image?"},
       {
         "type": "image_url",
         "image_url": {
           "url": "data:image/jpeg;base64,your_base64_encoded_image"
         }
       }
     ]
   }
 ]
}'
```

### 1.3. POST /completions
Handles text completions. This endpoint takes a prompt and returns a generated response.

```
curl -X POST https://api.arliai.com/v1/completions \
-H "Content-Type: application/json" \
-H "Authorization: Bearer your_api_key" \
-d '{
  "model": "MODEL_NAME",
  "prompt": "Once upon a time",
  "max_completion_tokens": 50
}'
```

### 1.4. POST /tokenize
Tokenizes the given text.

```
curl -X POST https://api.arliai.com/v1/tokenize \
-H "Content-Type: application/json" \
-H "Authorization: Bearer your_api_key" \
-d '{
  "model": "MODEL_NAME",
  "prompt": "Hello, world!"
}'
```

> model is optional for the /tokenize endpoint. If not provided, the API will use a default tokenizer.