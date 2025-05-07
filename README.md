# YouTube Chapter Generator (YCG)

A Chrome extension that automatically generates YouTube video chapters using AI, with a credit-based system for monetization.

## Features

- Extracts transcripts directly from YouTube videos
- Uses OpenAI GPT-4o to generate meaningful chapters based on content
- Creates properly formatted YouTube chapters ready to copy
- Simple, user-friendly interface
- Works with any YouTube video that has captions/subtitles
- Supports Decodo proxies to avoid IP blocks
- **NEW**: Credit-based system with multiple pricing plans
- **NEW**: User accounts with Google sign-in

## Pricing Plans

- **Free Plan**: 3 credits upon registration
- **Basic Plan**: 10 credits for $9
- **Premium Plan**: 50 credits for $29

## Credit System

- Each user starts with 3 free credits upon signup
- Initial chapter generation for a video costs 1 credit
- The first 2 regenerations for the same video are free (included with the initial credit)
- After the first 3 generations (initial + 2 free regenerations), another credit is used
- The next 2 regenerations are free (included with the second credit)
- Maximum of 6 generations per video (initial + 5 regenerations)

### Regeneration Logic

- When a user has exactly 1 credit and uses it for initial generation, they can still make up to 2 free regenerations even with 0 credits
- The backend checks if the user is entitled to a free regeneration before checking their credit balance
- This ensures users can utilize their full credit value even if their balance reaches 0

## How It Works

1. The extension extracts the video ID from the current YouTube page
2. It sends the video ID to our server
3. The server fetches the transcript using the YouTube Transcript API
4. The transcript is sent to OpenAI's API to analyze content and generate chapters
5. The generated chapters are returned to the extension and displayed to the user

## Technology Stack

- **Frontend**: Chrome Extension with vanilla JavaScript + React web interface with Tailwind CSS
- **Backend**: Python FastAPI (fully async) deployed on Vercel (ASGI server)
- **Database**: Redis (Upstash, async client) for user data and credit management
- **Authentication**: JWT-based with Google OAuth integration
- **Payments**: Stripe for secure payment processing
- **Libraries**:
  - YouTube Transcript API (for transcript extraction)
  - OpenAI API (for intelligent chapter generation)
  - FastAPI for API endpoints (async, with CORS support)
  - httpx (async HTTP client for all external I/O)
  - Upstash-redis (async Redis client)
  - PyJWT, python-jose, and Google Auth for authentication

## Backend Async Execution & Optimization

- **All endpoints and service calls are fully async** (`async def` + `await`).
- **All external I/O (HTTP, Redis, etc.) uses async libraries** (`httpx`, `upstash-redis`).
- **No blocking sync libraries** (such as `requests`) are used in the backend.
- **Deployment uses an ASGI server** (e.g., `uvicorn`) for true async support.
- **Tested and profiled for high concurrency and low latency**.

## Development

### Setup Backend

1. Install requirements:
```bash
pip install -r requirements.txt
```

2. Set up environment variables:
```
# API Keys
OPENAI_API_KEY=your_api_key_here
DECODO_USERNAME=your_decodo_username
DECODO_PASSWORD=your_decodo_password

# Authentication
JWT_SECRET_KEY=your_jwt_secret
GOOGLE_CLIENT_ID=your_google_client_id

# Database
REDIS_URL=your_redis_url

# Payment Processing
STRIPE_SECRET_KEY=your_stripe_secret
STRIPE_WEBHOOK_SECRET=your_stripe_webhook_secret
```

3. Run locally:
```bash
uvicorn api.index:app --reload
```

### Deployment Notes

- The backend is designed for ASGI servers (e.g., `uvicorn`, Vercel's Python builder).
- All endpoints are async and non-blocking.
- For local development, run:
  ```bash
  uvicorn api.index:app --reload
  ```
- For production (Vercel), deployment is automatic and uses ASGI by default.

## Project Structure Migration (April 2025)

**The project is now split into two Vercel deployments:**

- **Backend (API):** https://ycg-backend.vercel.app
  - Contains all FastAPI backend code, Stripe integration, and API endpoints.
  - Environment variable `FRONTEND_URL` should be set to `https://ycg-frontend.vercel.app`.

- **Frontend (Static/Extension):** https://ycg-frontend.vercel.app
  - Contains all static files and Chrome extension assets (see `new-ycg-frontend` repo).
  - Stripe payment success/cancel URLs now point to this domain.

### Migration Steps
1. All static files and extension assets moved to a new repo/project: `new-ycg-frontend`.
2. Stripe redirect URLs and backend config updated to use the new frontend domain.
3. CORS enabled on backend for the frontend domain.
4. All extension API calls must use the backend domain: `https://ycg-backend.vercel.app`.

**See the `README.md` in the frontend repo for details on static/extension deployment.**

## Deployment

The backend is automatically deployed to Vercel when changes are pushed to the main branch.

### Vercel Environment Variables

To ensure proper functionality, set these environment variables in your Vercel project:

1. `OPENAI_API_KEY` - Your OpenAI API key
2. `DECODO_USERNAME` - Your Decodo proxy username
3. `DECODO_PASSWORD` - Your Decodo proxy password
4. `JWT_SECRET_KEY` - Secret key for JWT token generation
5. `GOOGLE_CLIENT_ID` - Google OAuth client ID
6. `REDIS_URL` - Upstash Redis connection URL
7. `STRIPE_SECRET_KEY` - Stripe API secret key
8. `STRIPE_WEBHOOK_SECRET` - Stripe webhook secret for verifying events

## Proxy Provider (Decodo)

This project uses [Decodo Residential Proxies](https://help.decodo.com/docs/residential-proxy-quick-start) for all YouTube requests.

### Required Environment Variables

On Vercel (or locally), set the following:

- `DECODO_USERNAME`: Your Decodo proxy username
- `DECODO_PASSWORD`: Your Decodo proxy password

These are used to construct the proxy URL:

```
http://<DECODO_USERNAME>:<DECODO_PASSWORD>@gate.decodo.com:10001
```

The backend will automatically use this proxy for all outbound requests to YouTube.

### Example Usage (Python)

```python
import requests
url = 'https://ip.decodo.com/json'
username = 'YOUR_USERNAME'
password = 'YOUR_PASSWORD'
proxy = f"http://{username}:{password}@gate.decodo.com:10001"
result = requests.get(url, proxies = {
    'http': proxy,
    'https': proxy
})
print(result.text)
```

If these variables are not set, the backend will attempt direct connections and may be rate-limited by YouTube.

## Authentication Setup

To set up Google OAuth authentication:

1. Create a project in the [Google Cloud Console](https://console.cloud.google.com/)
2. Configure the OAuth consent screen
3. Create OAuth 2.0 credentials (Web application type)
4. Add your authorized JavaScript origins and redirect URIs
5. Copy the Client ID to your environment variables

## Stripe Integration

To set up Stripe for payment processing:

1. Create a [Stripe account](https://stripe.com/)
2. Get your API keys from the Stripe Dashboard
3. Set up products and prices for your credit packages
4. Configure webhooks to point to your Vercel deployment
5. Add the Stripe secrets to your environment variables

## Troubleshooting

### CORS Issues
If you see CORS errors in the console:
- Ensure the Vercel deployment has completed
- Check that the API is accessible
- Verify that the headers in vercel.json are correct
- Check browser console for specific error messages

### Proxy Issues
If the proxy is not working:
- Check the Decodo account status
- Verify the credentials are correct
- Ensure you're using Residential proxies (not other types)
- Check the server logs for connection errors

### Authentication Issues
If authentication is not working:
- Verify that the Google OAuth credentials are correct
- Check that the authorized domains are properly configured
- Ensure the JWT secret is properly set
- Check browser console for specific error messages

## License

This project is licensed under the MIT License.

## Latest Updates

- **May 7, 2025**: Fixed free regeneration logic to allow users with 0 credits to use their entitled free regenerations.
- **April 16, 2025**: Backend is now fully async, all blocking code removed, and optimized for concurrency and performance.
