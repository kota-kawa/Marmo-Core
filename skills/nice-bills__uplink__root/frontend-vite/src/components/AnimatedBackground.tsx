/**
 * Subtle background for inner pages (home uses fullscreen video instead)
 */

export function AnimatedBackground() {
  return (
    <div
      className="pointer-events-none fixed inset-0 z-0 bg-background"
      aria-hidden="true"
    />
  );
}
