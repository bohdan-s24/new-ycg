# Immediate Next Steps

## 1. Fix Google Login Issue

### 1.1 Content Security Policy
- Update manifest.json to allow Google API domains
- Fix CSP to allow necessary scripts and connections

### 1.2 Auth Container
- Add missing auth container to popup.html
- Ensure all required DOM elements are present

### 1.3 Google Sign-In Implementation
- Refactor auth.js to properly handle Google Sign-In
- Fix error handling and token exchange with backend

## 2. Backend Enhancements for Monetization

### 2.1 Credits Service Enhancement
- Update credits_service.py to support transactions
- Implement credit usage tracking
- Add transaction history functionality

### 2.2 Payment Integration
- Set up Stripe integration
- Create payment routes
- Implement webhook handling

### 2.3 API Endpoints
- Create endpoints for pricing plans
- Implement checkout session creation
- Add transaction history endpoint

## 3. Web Application Development

### 3.1 Project Setup
- Create Next.js project with Tailwind CSS
- Set up routing and layout components
- Configure API client for backend communication

### 3.2 Authentication Pages
- Implement login page
- Create registration page
- Add password reset functionality

### 3.3 Dashboard
- Create dashboard layout
- Implement credit balance display
- Add transaction history component
- Build chapter generation interface

### 3.4 Pricing and Checkout
- Create pricing page
- Implement checkout flow
- Add payment success/failure handling

## 4. Extension Updates

### 4.1 UI Enhancements
- Update popup.html with credit information
- Add links to web dashboard
- Improve error messaging

### 4.2 Credit-aware Generation
- Update generation flow to check credit balance
- Show appropriate messages for low/no credits
- Add redirect to purchase page

## 5. Testing and Deployment

### 5.1 Testing
- Test Google login flow
- Verify credit deduction on generation
- Test payment processing

### 5.2 Deployment
- Deploy backend updates to Vercel
- Deploy web application
- Package and test extension
