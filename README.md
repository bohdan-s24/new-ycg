# YouTube Chapter Generator (YCG)

A Chrome extension that automatically generates YouTube video chapters using AI, with a credit-based system for monetization.

## Features

- Extracts transcripts directly from YouTube videos
- Uses OpenAI GPT-4 to generate meaningful chapters based on content
- Creates properly formatted YouTube chapters ready to copy
- Simple, user-friendly interface
- Works with any YouTube video that has captions/subtitles
- Supports Webshare proxies to avoid IP blocks
- **NEW**: Credit-based system with multiple pricing plans
- **NEW**: User accounts with Google sign-in
- **NEW**: Web interface for account management and chapter generation

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
- **Backend**: Python Flask API deployed on Vercel
- **Database**: Redis (Upstash) for user data and credit management
- **Authentication**: JWT-based with Google OAuth integration
- **Payments**: Stripe for secure payment processing
- **Libraries**:
  - YouTube Transcript API (for transcript extraction)
  - OpenAI API (for intelligent chapter generation)
  - Flask for API endpoints (with CORS support)
  - Redis for data storage
  - PyJWT and Google Auth for authentication

## Development

### Setup Backend

1. Install requirements:
```
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
GOOGLE_CLIENT_SECRET=your_google_client_secret

# Database
REDIS_URL=your_redis_url

# Payment Processing
STRIPE_SECRET_KEY=your_stripe_secret
STRIPE_WEBHOOK_SECRET=your_stripe_webhook_secret
```

3. Run locally:
```
python main.py
```

### Setup Extension

1. Open Chrome and navigate to `chrome://extensions/`
2. Enable "Developer mode" in the top right
3. Click "Load unpacked" and select the `extension` folder

## Deployment

The backend is automatically deployed to Vercel when changes are pushed to the main branch.

### Vercel Environment Variables

To ensure proper functionality, set these environment variables in your Vercel project:

1. `OPENAI_API_KEY` - Your OpenAI API key
2. `WEBSHARE_USERNAME` - Your Webshare proxy username (if using Webshare)
3. `WEBSHARE_PASSWORD` - Your Webshare proxy password (if using Webshare)
4. `JWT_SECRET_KEY` - Secret key for JWT token generation
5. `GOOGLE_CLIENT_ID` - Google OAuth client ID
6. `GOOGLE_CLIENT_SECRET` - Google OAuth client secret
7. `REDIS_URL` - Upstash Redis connection URL
8. `STRIPE_SECRET_KEY` - Stripe API secret key
9. `STRIPE_WEBHOOK_SECRET` - Stripe webhook secret for verifying events

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
5. Copy the Client ID and Client Secret to your environment variables

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
Updated on April 7, 2025 with new monetization features, user authentication, and web interface.
