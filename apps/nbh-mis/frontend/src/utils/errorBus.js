// Tiny pub/sub so the axios interceptor (outside React) can notify the app
// shell about 5xx errors (toast) and 409s (no dataset -> show Upload) without
// a hard dependency on React context.

const errorSubscribers = new Set();
const unauthenticatedSubscribers = new Set();

export function publishError(message) {
  errorSubscribers.forEach((fn) => fn(message));
}

export function onError(fn) {
  errorSubscribers.add(fn);
  return () => errorSubscribers.delete(fn);
}

export function publishUnauthenticated(message) {
  unauthenticatedSubscribers.forEach((fn) => fn(message));
}

export function onUnauthenticated(fn) {
  unauthenticatedSubscribers.add(fn);
  return () => unauthenticatedSubscribers.delete(fn);
}
