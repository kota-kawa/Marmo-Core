import axios from 'axios';
import Echo from 'laravel-echo';
import Pusher from 'pusher-js';

window.axios = axios;
window.Pusher = Pusher;

window.axios.defaults.headers.common['X-Requested-With'] = 'XMLHttpRequest';

const csrfToken = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content');
const reverbKey = document.querySelector('meta[name="reverb-app-key"]')?.getAttribute('content');
const reverbHost = document.querySelector('meta[name="reverb-host"]')?.getAttribute('content') || window.location.hostname;
const reverbPort = document.querySelector('meta[name="reverb-port"]')?.getAttribute('content');
const reverbScheme = document.querySelector('meta[name="reverb-scheme"]')?.getAttribute('content') || window.location.protocol.replace(':', '');

if (reverbKey) {
	window.Echo = new Echo({
		broadcaster: 'reverb',
		key: reverbKey,
		wsHost: reverbHost,
		wsPort: reverbPort ? Number(reverbPort) : 80,
		wssPort: reverbPort ? Number(reverbPort) : 443,
		forceTLS: reverbScheme === 'https',
		enabledTransports: ['ws', 'wss'],
		authEndpoint: '/broadcasting/auth',
		auth: csrfToken
			? { headers: { 'X-CSRF-TOKEN': csrfToken } }
			: undefined,
	});
}
