/**
 * Sentry Error Reporting Helper for Supabase Edge Functions
 * 
 * Cara pakai di setiap edge function:
 *   import { reportError } from '../_shared/sentry.ts';
 *   ...
 *   } catch (error) {
 *     await reportError(error, { function: 'nama-function', extra: 'context' });
 *     ...
 *   }
 * 
 * WAJIB: Set secret SENTRY_DSN di Supabase Dashboard > Edge Functions > Secrets
 */

/**
 * Mengirim error ke Sentry via Sentry HTTP Envelope API.
 * Tidak bergantung pada SDK Deno — aman untuk semua versi runtime.
 * @param error - Error object yang ditangkap di catch block
 * @param context - Objek konteks tambahan (nama function, user_id, dll)
 */
export async function reportError(
  error: unknown,
  context: Record<string, string | number | boolean> = {}
): Promise<void> {
  const SENTRY_DSN = Deno.env.get('SENTRY_DSN');

  // Jika DSN tidak dikonfigurasi, skip tanpa melempar error
  if (!SENTRY_DSN) {
    console.warn('[Sentry] SENTRY_DSN tidak ditemukan. Error tidak akan dilaporkan ke Sentry.');
    return;
  }

  try {
    // Parse DSN: https://<public_key>@<host>/<project_id>
    const url = new URL(SENTRY_DSN);
    const publicKey = url.username;
    const host = url.hostname;
    const projectId = url.pathname.replace('/', '');
    const sentryEndpoint = `https://${host}/api/${projectId}/envelope/`;

    const errorMessage = error instanceof Error ? error.message : String(error);
    const errorStack = error instanceof Error ? error.stack : undefined;

    const now = Date.now() / 1000;

    // Format Sentry Envelope (standar Sentry v7+)
    const eventId = crypto.randomUUID().replace(/-/g, '');
    const envelope = [
      // Header envelope
      JSON.stringify({ event_id: eventId, sent_at: new Date().toISOString() }),
      // Item header
      JSON.stringify({ type: 'event', content_type: 'application/json' }),
      // Payload event
      JSON.stringify({
        event_id: eventId,
        timestamp: now,
        platform: 'javascript',
        level: 'error',
        logger: 'edge-function',
        environment: Deno.env.get('ENVIRONMENT') || 'staging',
        release: Deno.env.get('APP_VERSION') || 'tokcer-ai@unknown',
        exception: {
          values: [{
            type: error instanceof Error ? error.name : 'Error',
            value: errorMessage,
            stacktrace: errorStack ? {
              frames: errorStack.split('\n').slice(1).map(line => ({
                filename: line.trim(),
                function: '<anonymous>',
              }))
            } : undefined
          }]
        },
        tags: {
          runtime: 'deno',
          ...context
        },
        extra: context
      })
    ].join('\n');

    await fetch(sentryEndpoint, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/x-sentry-envelope',
        'X-Sentry-Auth': `Sentry sentry_version=7, sentry_key=${publicKey}, sentry_client=tokcer-edge/1.0`,
      },
      body: envelope,
    });

    console.log(`[Sentry] Error dilaporkan: ${errorMessage}`);
  } catch (sentryErr) {
    // Jangan sampai error di Sentry malah mengganggu response utama
    console.error('[Sentry] Gagal mengirim laporan error:', sentryErr);
  }
}
