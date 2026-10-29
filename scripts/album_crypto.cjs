// Native AES-GCM helper. Secrets travel only over stdin, never command arguments.
const fs = require('node:fs');
const crypto = require('node:crypto');
try {
    const request = JSON.parse(fs.readFileSync(0, 'utf8'));
    const bytes = key => Buffer.from(request[key], 'base64');
    let result;
    if (request.action === 'encrypt') {
        const cipher = crypto.createCipheriv('aes-256-gcm', bytes('key'), bytes('iv'));
        cipher.setAAD(bytes('associated'));
        result = Buffer.concat([cipher.update(bytes('data')), cipher.final(), cipher.getAuthTag()]);
    } else if (request.action === 'decrypt') {
        const ciphertext = bytes('data');
        const cipher = crypto.createDecipheriv('aes-256-gcm', bytes('key'), bytes('iv'));
        cipher.setAAD(bytes('associated'));
        cipher.setAuthTag(ciphertext.subarray(-16));
        result = Buffer.concat([cipher.update(ciphertext.subarray(0, -16)), cipher.final()]);
    } else {
        throw new Error('Unsupported operation');
    }
    process.stdout.write(result.toString('base64'));
} catch (_) {
    process.stderr.write('Album encryption or password verification failed.');
    process.exitCode = 1;
}
