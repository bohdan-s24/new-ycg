# YouTube Chapter Generator (YCG)

A Chrome extension that automatically generates YouTube video chapters using AI, with a credit-based system for monetization.

## Features

- Extracts transcripts directly from YouTube videos
- Uses OpenAI GPT-4o to generate meaningful chapters based on content
- Creates properly formatted YouTube chapters ready to copy
- Simple, user-friendly interface
- Works with any YouTube video that has captions/subtitles
- Supports Webshare proxies to avoid IP blocks
- **NEW**: Credit-based system with multiple pricing plans
- **NEW**: User accounts with Google sign-in

## Pricing Plans

- **Free Plan**: 3 credits upon registration (1 credit = 1 video with up to 5 generations)
- **Basic Plan**: 10 credits for $9
- **Premium Plan**: 50 credits for $29

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
WEBSHARE_USERNAME=your_webshare_username
WEBSHARE_PASSWORD=your_webshare_password

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

## Deployment

The backend is automatically deployed to Vercel when changes are pushed to the main branch.

### Vercel Environment Variables

To ensure proper functionality, set these environment variables in your Vercel project:

1. `OPENAI_API_KEY` - Your OpenAI API key
2. `WEBSHARE_USERNAME` - Your Webshare proxy username (if using Webshare)
3. `WEBSHARE_PASSWORD` - Your Webshare proxy password (if using Webshare)
4. `JWT_SECRET_KEY` - Secret key for JWT token generation
5. `GOOGLE_CLIENT_ID` - Google OAuth client ID
6. `REDIS_URL` - Upstash Redis connection URL
7. `STRIPE_SECRET_KEY` - Stripe API secret key
8. `STRIPE_WEBHOOK_SECRET` - Stripe webhook secret for verifying events

## Using Webshare Proxies

To avoid YouTube IP blocks, this project supports Webshare proxies:

1. **Purchase a Webshare Package**: 
   - Sign up for [Webshare](https://www.webshare.io/)
   - Purchase a "Residential" proxy package (NOT "Proxy Server" or "Static Residential")

2. **Configure Proxies**:
   - Find your proxy credentials in Webshare dashboard
   - Add them to your environment variables (see above)

3. **Vercel Configuration**:
   - Add the variables to your Vercel project settings
   - Redeploy the application

The API will automatically use the proxies if they are configured, falling back to direct access if not.

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
- Check the Webshare account status
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

## Latest Update
Updated on April 16, 2025: Backend is now fully async, all blocking code removed, and optimized for concurrency and performance.
