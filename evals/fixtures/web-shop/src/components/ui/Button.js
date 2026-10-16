export function Button({ label, variant = 'primary', disabled = false }) {
  return `<button class="btn btn-${variant}"${disabled ? ' disabled' : ''}>${label}</button>`;
}
