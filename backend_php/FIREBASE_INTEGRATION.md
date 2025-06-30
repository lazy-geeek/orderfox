# Firebase Integration for PHP Backend

## Overview
This document outlines the Firebase integration points for the OrderFox PHP backend using Firebase Admin SDK.

## Required Dependencies

Add to `composer.json`:
```json
{
    "require": {
        "kreait/firebase-php": "^7.0",
        "google/cloud-firestore": "^1.35"
    }
}
```

## Environment Variables

Add to `.env`:
```env
# Firebase Configuration
FIREBASE_PROJECT_ID=orderfox-dev
FIREBASE_PRIVATE_KEY_PATH=./config/firebase-service-account.json
FIREBASE_DATABASE_URL=https://orderfox-dev-default-rtdb.firebaseio.com/

# Firebase Emulator (Development)
FIREBASE_EMULATOR_HOST=localhost
FIREBASE_AUTH_EMULATOR_PORT=4001
FIREBASE_FIRESTORE_EMULATOR_PORT=4002
```

## Integration Points

### 1. User Authentication Integration
- **File**: `src/Services/AuthService.php`
- **Purpose**: Verify Firebase Auth tokens for API requests
- **Methods**:
  - `verifyFirebaseToken($token)` - Verify JWT token
  - `getUserFromToken($token)` - Extract user data from token

### 2. Trading Data Persistence
- **File**: `src/Services/TradingDataService.php`
- **Purpose**: Store trading sessions, orders, and portfolio data
- **Collections**:
  - `trading/{userId}/sessions/{sessionId}`
  - `trading/{userId}/orders/{orderId}`
  - `trading/{userId}/portfolio/{portfolioId}`

### 3. Market Data Caching
- **File**: `src/Services/MarketDataCacheService.php`
- **Purpose**: Cache market data for faster retrieval
- **Collections**:
  - `market_data/symbols`
  - `market_data/orderbooks/{symbol}`
  - `market_data/candles/{symbol}/{timeframe}`

### 4. Real-time Notifications
- **File**: `src/Services/NotificationService.php`
- **Purpose**: Send push notifications and real-time updates
- **Methods**:
  - `sendOrderNotification($userId, $orderData)`
  - `sendPriceAlert($userId, $alertData)`

## Firebase Factory Service

### File: `src/Core/FirebaseFactory.php`
```php
<?php

namespace OrderFox\Core;

use Kreait\Firebase\Factory;
use Kreait\Firebase\ServiceAccount;
use Google\Cloud\Firestore\FirestoreClient;

class FirebaseFactory
{
    private static $instance = null;
    private $firebase;
    private $firestore;
    
    private function __construct()
    {
        $this->initializeFirebase();
    }
    
    public static function getInstance(): FirebaseFactory
    {
        if (self::$instance === null) {
            self::$instance = new self();
        }
        return self::$instance;
    }
    
    private function initializeFirebase(): void
    {
        $config = Config::getInstance();
        
        if ($config->get('FIREBASE_EMULATOR_HOST')) {
            // Development with emulators
            $this->initializeWithEmulators($config);
        } else {
            // Production with real Firebase
            $this->initializeProduction($config);
        }
    }
    
    private function initializeWithEmulators(Config $config): void
    {
        $emulatorHost = $config->get('FIREBASE_EMULATOR_HOST', 'localhost');
        $authPort = $config->get('FIREBASE_AUTH_EMULATOR_PORT', '4001');
        $firestorePort = $config->get('FIREBASE_FIRESTORE_EMULATOR_PORT', '4002');
        
        // Set emulator environment variables
        putenv("FIREBASE_AUTH_EMULATOR_HOST={$emulatorHost}:{$authPort}");
        putenv("FIRESTORE_EMULATOR_HOST={$emulatorHost}:{$firestorePort}");
        
        $this->firebase = (new Factory)
            ->withProjectId($config->get('FIREBASE_PROJECT_ID'))
            ->create();
            
        $this->firestore = new FirestoreClient([
            'projectId' => $config->get('FIREBASE_PROJECT_ID')
        ]);
    }
    
    private function initializeProduction(Config $config): void
    {
        $serviceAccount = ServiceAccount::fromJsonFile(
            $config->get('FIREBASE_PRIVATE_KEY_PATH')
        );
        
        $this->firebase = (new Factory)
            ->withServiceAccount($serviceAccount)
            ->withProjectId($config->get('FIREBASE_PROJECT_ID'))
            ->create();
            
        $this->firestore = new FirestoreClient([
            'projectId' => $config->get('FIREBASE_PROJECT_ID'),
            'keyFilePath' => $config->get('FIREBASE_PRIVATE_KEY_PATH')
        ]);
    }
    
    public function getAuth()
    {
        return $this->firebase->createAuth();
    }
    
    public function getFirestore(): FirestoreClient
    {
        return $this->firestore;
    }
    
    public function getMessaging()
    {
        return $this->firebase->createMessaging();
    }
}
```

## Usage Examples

### Verifying Authentication Token
```php
use OrderFox\Core\FirebaseFactory;

$auth = FirebaseFactory::getInstance()->getAuth();
try {
    $verifiedIdToken = $auth->verifyIdToken($token);
    $userId = $verifiedIdToken->claims()->get('sub');
    // User is authenticated
} catch (\Exception $e) {
    // Invalid token
}
```

### Storing Trading Data
```php
use OrderFox\Core\FirebaseFactory;

$firestore = FirebaseFactory::getInstance()->getFirestore();
$collection = $firestore->collection('trading')
    ->document($userId)
    ->collection('orders');

$collection->add([
    'symbol' => 'BTCUSDT',
    'type' => 'market',
    'side' => 'buy',
    'quantity' => 0.001,
    'timestamp' => new \DateTime(),
    'status' => 'filled'
]);
```

## Security Considerations

1. **Service Account Key**: Never commit the service account JSON file to git
2. **Environment Variables**: Use proper environment variable management
3. **Token Validation**: Always verify Firebase tokens before processing requests
4. **Firestore Rules**: Implement proper security rules in production
5. **Emulator Mode**: Only use emulators in development environment

## Testing with Emulators

1. Start Firebase emulators:
   ```bash
   firebase emulators:start
   ```

2. Set emulator environment variables in PHP:
   ```php
   putenv('FIREBASE_AUTH_EMULATOR_HOST=localhost:4001');
   putenv('FIRESTORE_EMULATOR_HOST=localhost:4002');
   ```

3. Use emulator UI at http://localhost:4004 for testing

## Next Steps

1. Install Firebase Admin SDK: `composer require kreait/firebase-php`
2. Obtain Firebase service account key from Firebase Console
3. Implement AuthService for token verification
4. Implement TradingDataService for data persistence
5. Add Firebase integration to WebSocket handlers
6. Test with Firebase emulators