export async function enablePushNotifications() {
  if (!('Notification' in window)) return { enabled: false, reason: 'Browser notifications are not supported on this device.' };
  if (!('serviceWorker' in navigator)) return { enabled: false, reason: 'Service workers are not supported in this browser.' };

  const permission = await Notification.requestPermission();
  if (permission !== 'granted') return { enabled: false, reason: `Notification permission: ${permission}` };

  await navigator.serviceWorker.register('/sw.js');
  return {
    enabled: true,
    reason: 'Browser notifications enabled. In-app scheduled notifications remain stored in Supabase.',
  };
}
