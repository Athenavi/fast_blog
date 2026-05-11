/**
 * Emergency Fix Script
 * Run this in browser console to fix infinite refresh
 */

console.log('🚑 Running emergency fix...');

// 1. Unregister all Service Workers
if ('serviceWorker' in navigator) {
    navigator.serviceWorker.getRegistrations().then(function (registrations) {
        registrations.forEach(function (registration) {
            registration.unregister();
            console.log('✅ Service Worker unregistered:', registration.scope);
        });
    });
}

// 2. Clear all caches
if ('caches' in window) {
    caches.keys().then(function (names) {
        names.forEach(function (name) {
            caches.delete(name);
            console.log('✅ Cache deleted:', name);
        });
    });
}

// 3. Clear problematic cookies
document.cookie.split(';').forEach(function (cookie) {
    var name = cookie.split('=')[0].trim();
    if (name) {
        document.cookie = name + '=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;';
        console.log('✅ Cookie cleared:', name);
    }
});

// 4. Clear localStorage
try {
    localStorage.clear();
    console.log('✅ LocalStorage cleared');
} catch (e) {
    console.error('❌ Cannot clear localStorage:', e);
}

// 5. Clear sessionStorage
try {
    sessionStorage.clear();
    console.log('✅ SessionStorage cleared');
} catch (e) {
    console.error('❌ Cannot clear sessionStorage:', e);
}

console.log('✅ Emergency fix completed!');
console.log('⚠️ Please refresh the page now (Ctrl+Shift+R)');
