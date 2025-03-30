import { Notify } from 'quasar';

/**
 * Copies text to clipboard and shows a notification
 * @param text - Text to copy to clipboard
 * @param message - Optional custom message for the notification (defaults to "Copied to clipboard")
 */
export const copyToClipboard = (text: string, message = 'Copied to clipboard') => {
    navigator.clipboard.writeText(text)
        .then(() => {
            Notify.create({
                message,
                color: 'positive',
                position: 'top',
                timeout: 1500
            });
        })
        .catch(err => {
            console.error('Failed to copy text: ', err);
            Notify.create({
                message: 'Failed to copy',
                color: 'negative',
                position: 'top'
            });
        });
};
