/* EDF-header anonimiseren in de browser, vóór verzenden.
 *
 * Spiegel van myproject/edf_anonymize.py — dezelfde velden, dezelfde regels,
 * hetzelfde SHA-256-pseudoniem. Wijkt er één af, dan levert dezelfde opname via
 * de twee routes twee verschillende codes op en zijn ze niet meer aan elkaar te
 * koppelen. Wijzig ze samen.
 *
 * De header is 256 bytes ASCII; alleen twee velden dragen identificatie:
 *   offset  8, 80 bytes  patiëntveld  — code, geslacht, geboortedatum, naam
 *   offset 88, 80 bytes  opnameveld   — startdatum, ziekenhuis, technicus
 * De signaaldata wordt niet aangeraakt: we bouwen een Blob van [nieuwe header,
 * file.slice(256)], en die slice is een luie verwijzing — er wordt niets van de
 * gigabytes ingelezen of gekopieerd.
 */
(function (global) {
  'use strict';

  const PATIENT_OFFSET = 8, PATIENT_LEN = 80;
  const RECORDING_OFFSET = 88, RECORDING_LEN = 80;
  const DATE_OFFSET = 168, DATE_LEN = 8;
  const HEADER_LEN = 256;
  const DATE_UNKNOWN = '01.01.85';

  function readField(bytes, offset, len) {
    let s = '';
    for (let i = offset; i < offset + len; i++) s += String.fromCharCode(bytes[i]);
    return s.trim();
  }

  function writeField(bytes, offset, len, value) {
    const padded = value.slice(0, len).padEnd(len, ' ');
    for (let i = 0; i < len; i++) {
      const code = padded.charCodeAt(i);
      bytes[offset + i] = code < 128 ? code : 63; // '?' voor niet-ASCII
    }
  }

  async function pseudonym(original, prefix) {
    const data = new TextEncoder().encode(original);
    const digest = await crypto.subtle.digest('SHA-256', data);
    const hex = Array.from(new Uint8Array(digest))
      .map((b) => b.toString(16).padStart(2, '0')).join('');
    return `${prefix}_${hex.slice(0, 8).toUpperCase()}`;
  }

  const STUDY_CODE_MAX = 40;

  /* Alleen letters, cijfers en _-. — spaties zouden een extra subveld worden en
   * de EDF+-structuur van het patiëntveld breken. Spiegelt sanitize_study_code(). */
  function sanitizeStudyCode(code) {
    if (!code) return '';
    return String(code).trim()
      .split('')
      .filter((c) => /[A-Za-z0-9_.-]/.test(c))
      .join('')
      .slice(0, STUDY_CODE_MAX);
  }

  async function anonymizePatientField(original, prefix, keepSex, studyCode) {
    const override = sanitizeStudyCode(studyCode);
    const parts = original.split(/\s+/).filter(Boolean);
    if (parts.length >= 4) {
      const code = parts[0];
      const sexRaw = (parts[1] || '').toUpperCase();
      const sex = (keepSex && ['M', 'F', 'X'].includes(sexRaw)) ? sexRaw : 'X';
      const anonCode = override
        || (code.toUpperCase() === 'X' ? 'X' : await pseudonym(code, prefix));
      return `${anonCode} ${sex} X X`;
    }
    if (override) return override;
    if (original.trim() && original.trim().toUpperCase() !== 'X') {
      return await pseudonym(original, prefix);
    }
    return 'X';
  }

  function anonymizeRecordingField(original, keepStartdate) {
    const parts = original.split(/\s+/).filter(Boolean);
    if (parts.length >= 2 && parts[0].toLowerCase() === 'startdate') {
      const startdate = keepStartdate ? parts[1] : 'X';
      return `Startdate ${startdate} X X X`;
    }
    return 'X';
  }

  /** Lees de headervelden zonder iets te wijzigen. */
  async function readIdentifiers(file) {
    const head = new Uint8Array(await file.slice(0, HEADER_LEN).arrayBuffer());
    if (head.length < HEADER_LEN) throw new Error('geen geldige EDF-header');
    return {
      patient: readField(head, PATIENT_OFFSET, PATIENT_LEN),
      recording: readField(head, RECORDING_OFFSET, RECORDING_LEN),
      startdate: readField(head, DATE_OFFSET, DATE_LEN),
    };
  }

  /**
   * Geef een Blob terug met een geanonimiseerde header en ongewijzigde data,
   * plus de oude en nieuwe veldwaarden zodat de UI kan tonen wat er weggaat.
   */
  async function anonymizeFile(file, opts) {
    const o = Object.assign(
      { prefix: 'ANON', keepSex: true, keepStartdate: true, studyCode: '' }, opts || {});
    const head = new Uint8Array(await file.slice(0, HEADER_LEN).arrayBuffer());
    if (head.length < HEADER_LEN) throw new Error('geen geldige EDF-header');

    const before = {
      patient: readField(head, PATIENT_OFFSET, PATIENT_LEN),
      recording: readField(head, RECORDING_OFFSET, RECORDING_LEN),
      startdate: readField(head, DATE_OFFSET, DATE_LEN),
    };

    writeField(head, PATIENT_OFFSET, PATIENT_LEN,
      await anonymizePatientField(before.patient, o.prefix, o.keepSex, o.studyCode));
    writeField(head, RECORDING_OFFSET, RECORDING_LEN,
      anonymizeRecordingField(before.recording, o.keepStartdate));
    if (!o.keepStartdate) writeField(head, DATE_OFFSET, DATE_LEN, DATE_UNKNOWN);

    const after = {
      patient: readField(head, PATIENT_OFFSET, PATIENT_LEN),
      recording: readField(head, RECORDING_OFFSET, RECORDING_LEN),
      startdate: readField(head, DATE_OFFSET, DATE_LEN),
    };

    return { blob: new Blob([head, file.slice(HEADER_LEN)]), before, after };
  }

  /** Bestandsnaam zonder identificatie — de naam staat er vaker in dan in de header. */
  function safeFilename(code) {
    return `${(code || 'ANON').replace(/[^A-Za-z0-9_-]/g, '')}.edf`;
  }

  global.EdfAnonymize = {
    readIdentifiers, anonymizeFile, safeFilename, pseudonym, sanitizeStudyCode,
    // De veldfuncties zijn geen publieke API maar worden wel getoetst: een
    // test in Node vergelijkt ze veld voor veld met edf_anonymize.py, zodat
    // de twee implementaties niet stil uit elkaar lopen.
    __test: {
      patientField: anonymizePatientField,
      recordingField: anonymizeRecordingField,
    },
  };
})(window);
