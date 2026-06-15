import './bootstrap';

const root = document.documentElement;
const storedTheme = localStorage.getItem('theme');
const prefersDark = window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;
const initialTheme = storedTheme || (prefersDark ? 'dark' : 'light');

root.setAttribute('data-theme', initialTheme);

const toggle = document.getElementById('theme-toggle');

if (toggle) {
	const lightLabel = toggle.dataset.light || 'Light mode';
	const darkLabel = toggle.dataset.dark || 'Dark mode';

	const setLabel = (theme) => {
		const nextLabel = theme === 'dark' ? darkLabel : lightLabel;
		toggle.setAttribute('aria-label', nextLabel);
		toggle.setAttribute('title', nextLabel);
		toggle.setAttribute('aria-pressed', theme === 'dark');
	};

	setLabel(initialTheme);

	toggle.addEventListener('click', () => {
		const current = root.getAttribute('data-theme');
		const next = current === 'dark' ? 'light' : 'dark';
		root.setAttribute('data-theme', next);
		localStorage.setItem('theme', next);
		setLabel(next);
	});
}

const pageLoader = document.getElementById('page-loader');

if (pageLoader) {
	window.addEventListener('load', () => {
		pageLoader.classList.add('is-hidden');
		setTimeout(() => {
			pageLoader.remove();
		}, 500);
	});
}

const toasts = document.querySelectorAll('[data-toast]');

toasts.forEach((toast) => {
	const closeButton = toast.querySelector('[data-toast-close]');
	let dismissed = false;

	const dismiss = () => {
		if (dismissed) {
			return;
		}
		dismissed = true;
		toast.classList.add('is-hidden');
		setTimeout(() => {
			toast.remove();
		}, 250);
	};

	if (closeButton) {
		closeButton.addEventListener('click', dismiss);
	}

	setTimeout(dismiss, 5000);
});

const projectModal = document.getElementById('project-modal');

if (projectModal) {
	const openButtons = document.querySelectorAll('[data-modal-open="project-modal"]');
	const closeButtons = projectModal.querySelectorAll('[data-modal-close]');
	const steps = Array.from(projectModal.querySelectorAll('.modal-step'));
	const nextButton = projectModal.querySelector('[data-step-next]');
	const prevButton = projectModal.querySelector('[data-step-prev]');
	const publishButton = projectModal.querySelector('[data-step-publish]');
	const actionButtons = projectModal.querySelectorAll('[data-action-button]');
	const actionInput = projectModal.querySelector('[data-action-input]');
	const redirectInput = projectModal.querySelector('[data-redirect-input]');
	const modalForm = projectModal.querySelector('form.modal-form');
	let currentStep = 0;
	let submitIntent = false;

	const updateSteps = () => {
		steps.forEach((step, index) => {
			step.classList.toggle('is-active', index === currentStep);
		});
		if (prevButton) {
			prevButton.disabled = currentStep === 0;
		}
		if (nextButton) {
			nextButton.style.display = currentStep < steps.length - 1 ? '' : 'none';
		}
		if (publishButton) {
			publishButton.style.display = currentStep === steps.length - 1 ? '' : 'none';
		}
	};

	const openModal = () => {
		projectModal.classList.add('is-open');
		document.body.classList.add('modal-open');
		currentStep = 0;
		submitIntent = false;
		if (actionInput) {
			actionInput.value = 'draft';
		}
		if (redirectInput) {
			redirectInput.value = 'dashboard.index';
		}
		updateSteps();
	};

	const closeModal = () => {
		projectModal.classList.remove('is-open');
		document.body.classList.remove('modal-open');
	};

	openButtons.forEach((button) => {
		button.addEventListener('click', openModal);
	});

	closeButtons.forEach((button) => {
		button.addEventListener('click', closeModal);
	});

	projectModal.addEventListener('click', (event) => {
		if (event.target === projectModal) {
			closeModal();
		}
	});

	if (nextButton) {
		nextButton.addEventListener('click', () => {
			currentStep = Math.min(currentStep + 1, steps.length - 1);
			updateSteps();
		});
	}

	if (prevButton) {
		prevButton.addEventListener('click', () => {
			currentStep = Math.max(currentStep - 1, 0);
			updateSteps();
		});
	}

	if (actionButtons.length) {
		actionButtons.forEach((button) => {
			button.addEventListener('click', () => {
				submitIntent = true;
				if (actionInput) {
					actionInput.value = button.dataset.actionButton || 'draft';
				}
				if (redirectInput) {
					redirectInput.value = button.dataset.redirect || 'dashboard.index';
				}
			});
		});
	}

	if (modalForm) {
		modalForm.addEventListener('submit', (event) => {
			if (!submitIntent) {
				event.preventDefault();
			}
		});

		modalForm.addEventListener('keydown', (event) => {
			if (event.key === 'Enter' && event.target.tagName !== 'TEXTAREA') {
				event.preventDefault();
			}
		});
	}

	document.addEventListener('keydown', (event) => {
		if (event.key === 'Escape' && projectModal.classList.contains('is-open')) {
			closeModal();
		}
	});
}

const messageModal = document.getElementById('message-modal');

if (messageModal) {
	const openButtons = document.querySelectorAll('[data-modal-open="message-modal"]');
	const closeButtons = messageModal.querySelectorAll('[data-modal-close]');
	const projectIdInput = messageModal.querySelector('[data-message-project-id]');
	const projectTitleText = messageModal.querySelector('[data-message-project-title]');
	const designerNameText = messageModal.querySelector('[data-message-designer-name]');
	const messageField = messageModal.querySelector('textarea[name="message"]');

	const openModal = (button) => {
		if (projectIdInput) {
			projectIdInput.value = button.dataset.projectId || '';
		}
		if (projectTitleText) {
			projectTitleText.textContent = button.dataset.projectTitle || 'this project';
		}
		if (designerNameText) {
			designerNameText.textContent = button.dataset.designerName || 'the designer';
		}
		if (messageField) {
			messageField.value = '';
		}
		messageModal.classList.add('is-open');
		document.body.classList.add('modal-open');
	};

	const closeModal = () => {
		messageModal.classList.remove('is-open');
		document.body.classList.remove('modal-open');
	};

	openButtons.forEach((button) => {
		button.addEventListener('click', () => openModal(button));
	});

	closeButtons.forEach((button) => {
		button.addEventListener('click', closeModal);
	});

	messageModal.addEventListener('click', (event) => {
		if (event.target === messageModal) {
			closeModal();
		}
	});

	document.addEventListener('keydown', (event) => {
		if (event.key === 'Escape' && messageModal.classList.contains('is-open')) {
			closeModal();
		}
	});
}

const inquiriesRoot = document.querySelector('[data-inquiries-root]');

if (inquiriesRoot && window.Echo) {
	const designerId = inquiriesRoot.dataset.designerId;
	const list = inquiriesRoot.querySelector('[data-inquiries-list]');
	const emptyCard = inquiriesRoot.querySelector('[data-inquiries-empty]');
	const updateUrlBase = inquiriesRoot.dataset.inquiryUpdateUrlBase;
	const csrfToken = inquiriesRoot.dataset.csrf;
	const statusLabels = {
		pending: inquiriesRoot.dataset.statusPending || 'Pending',
		replied: inquiriesRoot.dataset.statusReplied || 'Replied',
		closed: inquiriesRoot.dataset.statusClosed || 'Closed',
	};
	const clientLabel = inquiriesRoot.dataset.labelClient || 'Client';
	const projectFallback = inquiriesRoot.dataset.projectFallback || 'Project';
	const nameFallback = inquiriesRoot.dataset.visitorFallback || 'Visitor';

	const buildInquiryCard = (inquiry) => {
		const card = document.createElement('article');
		card.className = 'card';
		card.dataset.inquiryId = String(inquiry.id);

		const cardTop = document.createElement('div');
		cardTop.className = 'card-top';

		const projectChip = document.createElement('span');
		projectChip.className = 'chip';
		projectChip.textContent = inquiry.project_title || projectFallback;

		const statusMeta = document.createElement('span');
		statusMeta.className = 'card-meta';
		statusMeta.textContent = statusLabels[inquiry.status] || inquiry.status;

		cardTop.append(projectChip, statusMeta);

		const heading = document.createElement('h3');
		heading.append(document.createTextNode(inquiry.visitor_name || nameFallback));

		if (inquiry.client_id) {
			const badge = document.createElement('span');
			badge.className = 'chip';
			badge.textContent = clientLabel;
			badge.style.backgroundColor = 'var(--color-primary)';
			badge.style.color = 'white';
			badge.style.fontSize = '0.7rem';
			badge.style.padding = '0.1rem 0.4rem';
			badge.style.marginLeft = '0.5rem';
			heading.append(badge);
		}

		const email = document.createElement('p');
		email.textContent = inquiry.visitor_email || '';

		const message = document.createElement('p');
		message.textContent = inquiry.message || '';

		card.append(cardTop, heading);
		if (email.textContent) {
			card.append(email);
		}
		card.append(message);

		if (updateUrlBase && csrfToken) {
			const form = document.createElement('form');
			form.className = 'form-row';
			form.method = 'post';
			form.action = `${updateUrlBase}/${inquiry.id}`;

			const tokenInput = document.createElement('input');
			tokenInput.type = 'hidden';
			tokenInput.name = '_token';
			tokenInput.value = csrfToken;

			const methodInput = document.createElement('input');
			methodInput.type = 'hidden';
			methodInput.name = '_method';
			methodInput.value = 'patch';

			const select = document.createElement('select');
			select.name = 'status';

			['pending', 'replied', 'closed'].forEach((status) => {
				const option = document.createElement('option');
				option.value = status;
				option.textContent = statusLabels[status] || status;
				if (inquiry.status === status) {
					option.selected = true;
				}
				select.append(option);
			});

			const button = document.createElement('button');
			button.className = 'btn btn-ghost';
			button.type = 'submit';
			button.textContent = inquiriesRoot.dataset.updateLabel || 'Update';

			form.append(tokenInput, methodInput, select, button);
			card.append(form);
		}

		return card;
	};

	if (designerId && list) {
		window.Echo.private(`designer.${designerId}`)
			.listen('.inquiry.created', (payload) => {
				const inquiry = payload?.inquiry || payload;
				if (!inquiry || !inquiry.id) {
					return;
				}
				if (list.querySelector(`[data-inquiry-id="${inquiry.id}"]`)) {
					return;
				}
				const card = buildInquiryCard(inquiry);
				list.prepend(card);
				if (emptyCard) {
					emptyCard.remove();
				}
			});
	}
}
