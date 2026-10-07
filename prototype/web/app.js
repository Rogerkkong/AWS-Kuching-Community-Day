/* MixUp Navigator - UI (app.js)
   Vanilla JS, no modules, no network. Renders the framed desktop window from design_ref/mockup_*.html
   and calls the engine through the single global `MX` (engine.js). If engine.js is missing, a small
   placeholder engine at the bottom of this file keeps the page rendering (see STUB).

   MX calls used (contract): MX.init, MX.reset, MX.setUser, MX.currentUser, MX.t, MX.data, MX.state,
   MX.canSee, MX.ask, MX.library, MX.document, MX.lineage, MX.whatChanged, MX.packs.{manifest,installed,
   checkUpdates,build,install}, MX.publisher.{analyzeUpload,commitUpload,pending,verify,demoUploadText},
   MX.notifications, MX.markRead, MX.evaluation, MX.analytics. */

var APP = (function () {
  'use strict';

  /* ------------------------------------------------------------------ labels (key -> [ms, en]) */
  var L = {
    app_name: ['MixUp Navigator', 'MixUp Navigator'],
    mode_officer: ['Mod Pegawai', 'Officer mode'], mode_publisher: ['Mod Penerbit', 'Publisher mode'],
    officer: ['Pegawai', 'Officer'], publisher: ['Penerbit', 'Publisher'],
    nav_ask: ['Tanya', 'Ask'], nav_library: ['Pekeliling', 'Circulars'], nav_updates: ['Kemas kini', 'Updates'],
    nav_verify: ['Pekeliling', 'Circulars'], nav_build: ['Bina pek', 'Build packs'], nav_eval: ['Penilaian', 'Evaluation'], nav_analytics: ['Analitik', 'Analytics'],
    offline: ['Luar talian', 'Offline'], offline_text: ['Dokumen dan soalan kekal di komputer ini.', 'Documents and questions stay on this computer.'],
    synthetic: ['SINTETIK – CONTOH SAHAJA', 'SINTETIK – CONTOH SAHAJA'], reset_demo: ['Set semula demo', 'Reset demo'],
    switch_officer: ['Tukar pegawai (demo)', 'Switch officer (demo)'], clearance: ['Klearans', 'Clearance'],
    sso_note: ['Prototaip: tiada kata laluan. Versi pengeluaran menggunakan log masuk agensi.', 'Prototype: no passwords. Production uses agency sign-in.'],
    jurisdiction: ['Bidang kuasa', 'Jurisdiction'], notifications: ['Notifikasi', 'Notifications'],
    notif_sub: ['Dijana semasa pek dipasang', 'Created when a pack is installed'], notif_none: ['Tiada notifikasi.', 'No notifications.'],
    banner_title: ['Kemas kini tersedia', 'Update available'], banner_btn: ['Lihat kemas kini', 'View update'],
    banner_body: ['Pek {pack} v{v} · {changes} · ditandatangani oleh penerbit', '{pack} pack v{v} · {changes} · signed by the publisher'],
    new_circulars: ['{n} pekeliling baharu', '{n} new circular(s)'], status_changes: ['{n} perubahan status', '{n} status change(s)'],
    // screen titles
    t_ask: ['Tanya', 'Ask'], s_ask: ['Jawapan bersumber daripada pekeliling berkuat kuasa', 'Cited answers from circulars in force'],
    t_library: ['Pekeliling', 'Circulars'], s_library: ['Semua dokumen dalam pek yang dibenarkan untuk anda', 'All documents in the packs you are cleared for'],
    t_updates: ['Kemas kini', 'Updates'], s_updates: ['Pek pengetahuan yang ditandatangani · disahkan sebelum dipasang', 'Signed knowledge packs · verified before install'],
    t_verify: ['Pekeliling', 'Circulars'], s_verify: ['Muat naik, hubungan yang diekstrak dan baris gilir pengesahan', 'Upload, extracted relations and the verification queue'],
    t_build: ['Bina pek', 'Build packs'], s_build: ['Satu pek bertandatangan bagi setiap peringkat klearans', 'One signed pack per clearance tier'],
    t_eval: ['Penilaian', 'Evaluation'], s_eval: ['Garis asas vs MixUp Navigator pada set emas', 'Baseline vs MixUp Navigator on the golden set'],
    t_analytics: ['Analitik', 'Analytics'], s_analytics: ['Apa yang ditanya pegawai dan apa yang dikecualikan', 'What officers ask and what gets excluded'],
    // ask
    hero_h: ['Tanya tentang peraturan yang berkuat kuasa hari ini.', 'Ask about the rules in force today.'],
    hero_p: ['Jawapan hanya diambil daripada pekeliling yang masih terpakai, dengan petikan perenggan dan halaman. Pekeliling yang dibatalkan akan dinyatakan, bukan dipetik.',
      'Answers come only from circulars still in force, citing the clause and page. Cancelled circulars are flagged, never quoted.'],
    try: ['Cuba', 'Try'], question: ['Soalan', 'Question'], answer: ['Jawapan', 'Answer'], cannot_answer: ['Tidak dapat dijawab', 'Cannot be answered'],
    tag_hero: ['Soalan utama', 'Hero question'], tag_trap: ['Soalan perangkap', 'Trap question'], tag_jur: ['Bidang kuasa', 'Jurisdiction'],
    tag_mixed: ['Bahasa campuran', 'Mixed language'], tag_unans: ['Tiada jawapan', 'Unanswerable'],
    placeholder: ['Tanya dalam Bahasa Melayu atau English…', 'Ask in English or Bahasa Melayu…'], ask_btn: ['Tanya', 'Ask'],
    include_hist: ['Sertakan pekeliling sejarah (dibatalkan)', 'Include historical (cancelled) circulars'],
    compare_chatbot: ['Bandingkan dengan chatbot biasa', 'Compare with a typical chatbot'],
    searching_in: ['Mencari dalam {packs}', 'Searching {packs}'], pack_terbuka: ['Pek Terbuka', 'Terbuka pack'], pack_both: ['Pek Terbuka + Terhad', 'Terbuka + Terhad packs'],
    pack_all: ['Pek Terbuka + Terhad + Sulit', 'Terbuka + Terhad + Sulit packs'],
    st_retrieving: ['Mencari dalam {n} pek · kata kunci, glosari, nombor pekeliling…', 'Searching {n} pack(s) · keyword, glossary, circular number…'],
    st_streaming: ['Sumber ditemui dalam {s} s · menyusun jawapan ekstraktif…', 'Sources found in {s} s · composing the extractive answer…'],
    st_final: ['Selesai · semua petikan disahkan', 'Done · all citations validated'], st_refused: ['Selesai · tiada sumber yang mencukupi', 'Done · not enough evidence'],
    excluded: ['Dikecualikan daripada jawapan', 'Excluded from this answer'], view_lineage: ['Lihat salasilah →', 'View lineage →'],
    confidence: ['Keyakinan', 'Confidence'], conf_HIGH: ['Tinggi', 'High'], conf_MEDIUM: ['Sederhana', 'Medium'], conf_LOW: ['Rendah', 'Low'],
    timing: ['Sumber {a} s · lengkap {b} s · enjin dalam pelayar', 'Sources {a} s · complete {b} s · in-browser engine'],
    helpful: ['Membantu', 'Helpful'], not_helpful: ['Tidak membantu', 'Not helpful'],
    jur_differs: ['Peraturan berbeza mengikut bidang kuasa', 'The rule differs by jurisdiction'], jur_first: ['Peraturan anda dipaparkan dahulu', 'Your rule is shown first'],
    your_rule: ['Peraturan anda', 'Your rule'], comparison: ['Perbandingan', 'Comparison'],
    typical: ['Chatbot biasa', 'Typical chatbot'], wrong: ['SALAH', 'WRONG'], wrong_why: ['memetik pekeliling yang dibatalkan', 'cites a cancelled circular'],
    navigator: ['MixUp Navigator', 'MixUp Navigator'], baseline_note: ['Tiada penapis status, tiada bidang kuasa, tiada senarai dikecualikan', 'No status filter, no jurisdiction logic, no excluded list'],
    // right panel
    tab_sources: ['Sumber', 'Sources'], tab_page: ['Halaman', 'Page'], tab_lineage: ['Salasilah', 'Lineage'],
    empty_idle: ['Sumber, halaman asal dan salasilah pindaan dipaparkan di sini sebaik carian selesai.', 'Sources, original pages and amendment lineage appear here as soon as the search finishes.'],
    empty_retrieving: ['Mencari petikan yang berkaitan…', 'Finding relevant passages…'],
    empty_refused: ['Tiada petikan daripada pekeliling berkuat kuasa yang cukup kukuh untuk menjawab soalan ini.', 'No passage from a circular in force is strong enough to answer this question.'],
    empty_page: ['Pilih sumber atau petikan [S#] untuk membuka halaman.', 'Pick a source or an [S#] chip to open its page.'],
    empty_lineage: ['Salasilah dipaparkan selepas carian.', 'Lineage appears after a search.'],
    open_page: ['Buka halaman →', 'Open page →'], p_abbr: ['hlm.', 'p.'],
    page_of: ['Halaman {a} daripada {b} · dokumen sintetik', 'Page {a} of {b} · synthetic document'],
    lineage_intro: ['Sejarah pindaan · lama ke baharu · hanya hubungan yang disahkan penerbit', 'Amendment history · oldest to newest · publisher-verified relations only'],
    what_changed: ['Apa yang berubah: ', 'What changed: '], hidden_doc: ['1 dokumen terhad disembunyikan', '1 restricted document hidden'],
    rel_CANCELS: ['MEMBATALKAN', 'CANCELS'], rel_SUPERSEDES: ['MENGGANTIKAN', 'SUPERSEDES'], rel_AMENDS: ['MEMINDA', 'AMENDS'], rel_REFERENCES: ['MERUJUK', 'REFERENCES'],
    // library
    col_no: ['Nombor', 'Number'], col_title: ['Tajuk', 'Title'], col_jur: ['Bidang kuasa', 'Jurisdiction'], col_status: ['Status', 'Status'], col_date: ['Tarikh', 'Date'], col_tier: ['Klearans', 'Clearance'],
    f_all: ['Semua', 'All'], f_valid: ['Masih terpakai', 'Still applies'], f_cancelled: ['Dibatalkan', 'Cancelled'],
    lib_foot_t1: ['Termasuk dokumen Terhad sintetik. Dokumen bertanda SINTETIK – CONTOH SAHAJA ialah bahan demo.', 'Includes synthetic Terhad documents. Documents marked SINTETIK – CONTOH SAHAJA are demo material.'],
    lib_foot_t0: ['Pek Terhad tidak dibuka untuk klearans Terbuka. Dokumen terhad tidak dipaparkan di mana-mana.', 'The Terhad pack does not open for Terbuka clearance. Restricted documents appear nowhere.'],
    lib_count: ['{n} dokumen', '{n} documents'], lib_empty: ['Tiada dokumen sepadan dengan penapis ini.', 'No documents match these filters.'],
    // updates
    channel: ['Saluran kemas kini', 'Update channel'], install_btn: ['Pasang Pek {pack} v{v}', 'Install {pack} pack v{v}'], tamper_btn: ['Simulasi pek diubah suai', 'Simulate tampered pack'],
    installed_active: ['Dipasang · v{v} aktif', 'Installed · v{v} active'], rejected_chip: ['Ditolak · v{v} kekal aktif', 'Rejected · v{v} stays active'],
    upd_note: ['Pek yang diubah suai atau tandatangan tidak sah akan ditolak, dan versi sebelumnya kekal aktif.', 'A tampered pack or invalid signature is rejected, and the previous version stays active.'],
    no_update: ['Tiada kemas kini baharu dalam saluran.', 'No new update on the channel.'],
    changed_title: ['Apa yang berubah · v{a} → v{b}', 'What changed · v{a} → v{b}'], changed_sub: ['Ringkasan disediakan oleh penerbit', 'Summaries prepared by the publisher'],
    k_new: ['Pekeliling baharu', 'New circular'], k_status: ['Status berubah', 'Status changed'], k_rel: ['Hubungan baharu', 'New relation'], k_upd: ['Kemas kini tersedia', 'Update available'], k_fail: ['Pemasangan ditolak', 'Install rejected'],
    installed_packs: ['Pek dipasang', 'Installed packs'], installed_on: ['Dipasang {d}', 'Installed {d}'], kept_rollback: ['v{v} disimpan untuk rollback', 'v{v} kept for rollback'],
    opened_terhad: ['Dibuka kerana klearans anda: {t}', 'Opened because your clearance is {t}'],
    pack_locked: ['Pek Terhad tidak dihantar ke peranti ini. Klearans anda: Terbuka.', 'The Terhad pack is not delivered to this device. Your clearance: Terbuka.'],
    documents_n: ['{n} dokumen', '{n} documents'], in_browser_index: ['indeks dalam pelayar', 'in-browser index'],
    step1: ['Baca manifest.json', 'Read manifest.json'], step2: ['Salin fail pek', 'Copy pack file'], step3: ['Sahkan checksum SHA-256', 'Verify SHA-256 checksum'],
    step4: ['Sahkan tandatangan Ed25519', 'Verify Ed25519 signature'], step5: ['Semak model pembenaman', 'Check embedding model'], step6: ['Pasang secara atomik', 'Install atomically'], step7: ['Bandingkan versi', 'Compare versions'],
    // publisher
    pub_intro: ['Hubungan yang diekstrak secara automatik tidak mengubah status sehingga disahkan. Hanya hubungan yang disahkan disalin ke dalam pek.',
      'Automatically extracted relations change no status until verified. Only verified relations are copied into packs.'],
    upload_t: ['Muat naik pekeliling', 'Upload a circular'], upload_s: ['Fail .md atau .txt. Metadata dan hubungan diekstrak dengan regex; tiada status berubah sehingga penerbit mengesahkannya.',
      '.md or .txt file. Metadata and relations are extracted by regex; no status changes until a publisher verifies them.'],
    choose_file: ['Pilih fail', 'Choose file'], demo_upload: ['Guna pekeliling demo SPP 1/2026', 'Use demo circular SPP 1/2026'],
    analysis_t: ['Analisis muat naik', 'Upload analysis'], meta_t: ['Metadata yang diekstrak', 'Extracted metadata'], relations_found: ['Hubungan dikesan ({n})', 'Detected relations ({n})'],
    no_relations: ['Tiada rujukan kepada pekeliling lain dikesan.', 'No references to other circulars detected.'],
    add_library: ['Tambah ke perpustakaan', 'Add to library'], discard: ['Buang', 'Discard'],
    added_msg: ['Ditambah sebagai {no} · status tidak berubah sehingga disahkan', 'Added as {no} · statuses unchanged until verified'],
    queue_t: ['Baris gilir pengesahan', 'Verification queue'], queue_empty: ['Tiada hubungan menunggu. Muat naik pekeliling untuk mengekstrak calon hubungan.', 'No relations waiting. Upload a circular to extract candidate relations.'],
    verify: ['Sahkan', 'Verify'], reject: ['Tolak', 'Reject'], extraction_conf: ['Keyakinan ekstraksi', 'Extraction confidence'],
    effect: ['kesan', 'effect'], no_effect: ['tiada perubahan status', 'no status change'],
    dec_ok: ['Disahkan · akan dimasukkan ke pek', 'Verified · will be included in the pack'], dec_no: ['Ditolak · tidak menjejaskan status', 'Rejected · no effect on status'],
    m_no: ['Nombor', 'Number'], m_title: ['Tajuk', 'Title'], m_issuer: ['Penerbit', 'Issuer'], m_issued: ['Dikeluarkan', 'Issued'], m_effective: ['Kuat kuasa', 'Effective'],
    m_class: ['Klasifikasi', 'Classification'], m_jur: ['Bidang kuasa', 'Jurisdiction'], m_pages: ['Halaman', 'Pages'], m_type: ['Jenis', 'Type'],
    // build
    included: ['Dimasukkan sejak v{v}', 'Included since v{v}'], build_sign: ['Bina dan tandatangan', 'Build and sign'], version: ['Versi', 'Version'],
    build_btn: ['Bina pek v{v}', 'Build packs v{v}'], publish_btn: ['Terbitkan ke saluran kemas kini', 'Publish to update channel'],
    published: ['Diterbitkan ke \\\\fs01 · manifest.json dikemas kini', 'Published to \\\\fs01 · manifest.json updated'],
    deliver_0: ['Dihantar ke semua peranti pegawai', 'Delivered to all officer devices'], deliver_1: ['Dihantar hanya ke peranti pegawai berklearans', 'Delivered to cleared officers only'],
    deliver_2: ['Dihantar hanya ke peranti berklearans Sulit', 'Delivered to Sulit-cleared devices only'],
    b1: ['Salin dokumen dan hubungan disahkan', 'Copy documents and verified relations'], b2: ['Bina indeks kata kunci', 'Build keyword index'],
    b3: ['Bina indeks nombor pekeliling', 'Build circular-number index'], b4: ['Sertakan ringkasan perubahan', 'Include change summaries'],
    b5: ['Kira SHA-256', 'Compute SHA-256'], b6: ['Tandatangan (Ed25519 · demo)', 'Sign (Ed25519 · demo stand-in)'],
    sig_note: ['tandatangan demo: dalam pengeluaran, kunci peribadi Ed25519 kekal di komputer penerbit', 'demo signature: in production the Ed25519 private key stays on the publisher’s computer'],
    c_tier: ['Peringkat', 'Tier'], c_ver: ['Versi', 'Version'], c_file: ['Fail', 'File'], c_sha: ['SHA-256', 'SHA-256'], c_sig: ['Tandatangan', 'Signature'], c_docs: ['Dokumen', 'Documents'],
    verified_rel: ['{n} hubungan disahkan', '{n} relations verified'], pending_rel: ['{n} menunggu pengesahan', '{n} awaiting verification'],
    // eval + analytics
    run_browser: ['Jalankan dalam pelayar', 'Run in browser'], running: ['Menjalankan…', 'Running…'],
    src_precomputed: ['Dikira awal oleh scripts/evaluate.py (Python)', 'Precomputed by scripts/evaluate.py (Python)'], src_browser: ['Dijalankan semula dalam pelayar ini dengan MX.ask', 'Re-run in this browser with MX.ask'],
    metric: ['Metrik', 'Metric'], baseline: ['Garis asas (RAG biasa)', 'Baseline (plain RAG)'], target: ['Sasaran', 'Target'], by_type: ['Mengikut jenis soalan (betul dan terkini)', 'By question type (correct and current)'],
    type: ['Jenis', 'Type'],
    m_correct: ['Jawapan betul & terkini', 'Correct & current answers'], m_cancelled: ['Kadar petikan dibatalkan', 'Cancelled-citation rate'], m_recall: ['Recall@5', 'Recall@5'], m_mrr: ['MRR', 'MRR'],
    m_cite: ['Ketepatan petikan', 'Citation accuracy'], m_jur_acc: ['Ketepatan bidang kuasa', 'Jurisdiction accuracy'], m_refusal: ['Ketepatan penolakan', 'Refusal accuracy'],
    m_false_refusal: ['Kadar penolakan palsu', 'False-refusal rate'], m_leaks: ['Kebocoran akses', 'Access leaks'], m_p50: ['Latensi p50', 'Latency p50'], m_p95: ['Latensi p95', 'Latency p95'],
    a_total: ['Soalan ditanya', 'Questions asked'], a_unanswered: ['Kadar tidak terjawab', 'Unanswered rate'], a_excluded: ['Pengecualian pekeliling dibatalkan', 'Cancelled-circular exclusions'], a_users: ['Pegawai aktif', 'Active officers'],
    a_top_q: ['Soalan paling kerap', 'Top questions'], a_top_ex: ['Pekeliling dibatalkan paling kerap dikecualikan', 'Cancelled circulars most often excluded'],
    a_none: ['Belum ada data – tanya soalan dahulu.', 'No data yet – ask a question first.'],
    // status bar
    net_offline: ['Rangkaian: luar talian', 'Network: offline'], engine_ready: ['Enjin: dalam pelayar · sedia', 'Engine: in-browser · ready'],
    local_note: ['file:// · tiada pelayan, tiada model, tiada rangkaian', 'file:// · no server, no model, no network'],
    // statuses / jurisdictions / tiers
    IN_FORCE: ['Berkuat kuasa', 'In force'], AMENDED: ['Dipinda', 'Amended'], CANCELLED: ['Dibatalkan', 'Cancelled'], UNKNOWN: ['Belum disahkan', 'Unverified'], ONE_OFF: ['Sekali sahaja', 'One-off'],
    FEDERAL: ['Persekutuan', 'Federal'], SARAWAK: ['Sarawak', 'Sarawak'], FEDERAL_SARAWAK: ['Persekutuan + Sarawak', 'Federal + Sarawak'], JUR_UNKNOWN: ['Tidak diketahui', 'Unknown'],
    role_OFFICER: ['Pegawai', 'Officer'], role_POLICY_OWNER: ['Pemilik dasar', 'Policy owner'], role_ADMIN: ['Pentadbir', 'Admin'],
    circular: ['pekeliling', 'circular'], guideline: ['garis panduan', 'guideline'], sop: ['SOP', 'SOP'], minutes: ['minit mesyuarat', 'minutes'], report: ['laporan', 'report'],
    in_force_from: ['berkuat kuasa {d}', 'in force from {d}'], status_arrow: ['{a} → {b}', '{a} → {b}'],
    loading: ['Memuatkan…', 'Loading…'], stub_warn: ['', '']
  };

  var SUGGESTIONS = [
    { ms: 'Berapakah kadar elaun perbatuan untuk tuntutan perjalanan?', en: 'What is the mileage rate for travel claims?', tag: 'tag_hero' },
    { ms: 'Berapa lama tempoh untuk mengemukakan tuntutan perjalanan?', en: 'Berapa lama tempoh untuk mengemukakan tuntutan perjalanan?', tag: 'tag_trap' },
    { ms: 'How many days of childcare leave can I take?', en: 'How many days of childcare leave can I take?', tag: 'tag_jur' },
    { ms: 'Boleh saya claim mileage kalau guna kereta sendiri?', en: 'Boleh saya claim mileage kalau guna kereta sendiri?', tag: 'tag_mixed' },
    { ms: 'What is the policy for private contractors working from home?', en: 'What is the policy for private contractors working from home?', tag: 'tag_unans' }
  ];
  var CHANNEL_PATH = '\\\\fs01.jpa.local\\pekeliling\\packs';
  var TIERS = ['Terbuka', 'Terhad', 'Sulit'];

  /* ------------------------------------------------------------------ small helpers */
  function lang() { return (window.MX && MX.state && MX.state.lang) || 'ms'; }
  function t(key, vars) {
    var pair = L[key], s;
    if (pair) s = pair[lang() === 'en' ? 1 : 0];
    else if (window.MX && typeof MX.t === 'function') s = MX.t(key);
    if (s == null) s = key;
    if (vars) Object.keys(vars).forEach(function (k) { s = s.split('{' + k + '}').join(String(vars[k])); });
    return s;
  }
  function esc(v) { return String(v == null ? '' : v).replace(/[&<>"']/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]; }); }
  function fmtDate(iso) {
    if (!iso) return '';
    var m = /^(\d{4})-(\d{2})-(\d{2})/.exec(String(iso));
    if (!m) return String(iso);
    var ms = ['Jan', 'Feb', 'Mac', 'Apr', 'Mei', 'Jun', 'Jul', 'Ogos', 'Sep', 'Okt', 'Nov', 'Dis'], en = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
    return parseInt(m[3], 10) + ' ' + (lang() === 'en' ? en : ms)[parseInt(m[2], 10) - 1] + ' ' + m[1];
  }
  function secs(ms) { return (Math.max(0, ms || 0) / 1000).toFixed(1); }
  function statusChip(st) { st = st || 'UNKNOWN'; return '<span class="status-chip st-' + esc(st) + '"><span class="dot"></span>' + esc(t(st)) + '</span>'; }
  function jurLabel(j) { return j ? t(L[j] ? j : 'JUR_UNKNOWN') : t('JUR_UNKNOWN'); }
  function tierLabel(n) { return TIERS[n | 0] || TIERS[0]; }
  function relLabel(type) { return t('rel_' + type) === 'rel_' + type ? type : t('rel_' + type); }
  function user() { return MX.currentUser() || (MX.data.users && MX.data.users[0]) || { name: '?', initials: '?', jurisdiction: 'FEDERAL', clearance_level: 0 }; }
  function initials(u) { return u.initials || (u.name || '?').split(/\s+/).map(function (w) { return w[0]; }).join('').slice(0, 2).toUpperCase(); }
  function docById(id) { return (MX.data.documents || []).filter(function (d) { return d.doc_id === id; })[0]; }
  function docNo(id) { var d = docById(id); return d ? (d.circular_no || d.doc_id) : id; }
  function packLabel() { var c = user().clearance_level | 0; return t(c >= 2 ? 'pack_all' : c >= 1 ? 'pack_both' : 'pack_terbuka'); }
  function clamp(s, n) { s = String(s || '').replace(/\s+/g, ' ').trim(); return s.length > n ? s.slice(0, n - 1).replace(/\s\S*$/, '') + '…' : s; }
  function keyFigure(text) {
    var s = String(text || ''), m = /RM\s?\d+(?:[.,]\d+)?(?:\s*(?:sekilometer|\/\s*km|per\s*km|km))?/i.exec(s)
      || /\b\d+\s*(?:hari|days?|minggu|weeks?|bulan|months?|kali|times|tahun|years?|km)\b(?:\s*(?:bekerja|working))?/i.exec(s)
      || /\b\d+\s*%/.exec(s);
    return m ? m[0] : null;
  }
  function firstSentence(text) { var s = String(text || '').replace(/\s+/g, ' ').trim(); var m = /^(.*?[.!?])(\s|$)/.exec(s); return clamp(m ? m[1] : s, 140); }
  function pick(o, keys, dflt) { for (var i = 0; i < keys.length; i++) { if (o && o[keys[i]] != null) return o[keys[i]]; } return dflt; }
  function bi(o, base) { // bilingual field: base_ms / base_en / base / {ms,en}
    if (!o) return '';
    var v = o[base + '_' + lang()]; if (v != null) return v;
    v = o[base]; if (v && typeof v === 'object') return v[lang()] || v.ms || v.en || '';
    if (v != null) return v;
    return o[base + '_ms'] || o[base + '_en'] || '';
  }
  function fmtBytes(n) { n = Number(n || 0); return n >= 1048576 ? (n / 1048576).toFixed(1) + ' MB' : n >= 1024 ? (n / 1024).toFixed(1) + ' KB' : n + ' B'; }
  function prefix(h, n) { h = String(h || ''); return h ? h.slice(0, n || 4) + '…' + h.slice(-4) : '—'; }
  function pct(v) { return (Number(v) * 100).toFixed(1) + '%'; }

  /* ------------------------------------------------------------------ UI state (engine state lives in MX.state) */
  var S;
  function freshState() {
    return {
      screen: 'ask', profileMenu: false, notifOpen: false, draft: '', compare: false,
      ask: { phase: 'idle', question: '', result: null, baseline: null, t0: 0, shown: 0, sourcesMs: 0, completeMs: 0, feedback: null },
      tab: 'sources', viewer: null, lineageDoc: null,
      lib: { status: 'all', jur: 'all', doc: null, tab: 'viewer', viewer: null },
      upd: { running: false, steps: null, shown: -1, result: null, failedAt: -1, tamper: false, lastTarget: null },
      pub: { analysis: null, filename: '', committed: null, decided: {} },
      build: { version: null, running: false, shown: -1, done: false, published: false, result: null },
      evalRes: null, evalSource: 'precomputed', evalRunning: false
    };
  }
  var timers = [];
  function later(fn, ms) { var id = setTimeout(fn, ms); timers.push(id); return id; }
  function clearTimers() { timers.forEach(clearTimeout); timers = []; }

  /* ------------------------------------------------------------------ render root */
  var root;
  function render() {
    var saved = {};
    root.querySelectorAll('[data-scroll]').forEach(function (el) { saved[el.getAttribute('data-scroll')] = el.scrollTop; });
    var mode = MX.state.mode, officer = mode === 'officer';
    document.documentElement.lang = lang();
    root.innerHTML =
      '<div class="win" data-screen-label="MixUp Navigator window">' +
        titleBar(officer) +
        '<div class="body">' + sidebar(officer) + '<main class="main">' + header() + notifPopover() + banner(officer) + screen(officer) + '</main></div>' +
        statusBar() +
      '</div>';
    Object.keys(saved).forEach(function (k) { var el = root.querySelector('[data-scroll="' + k + '"]'); if (el) el.scrollTop = saved[k]; });
  }

  function titleBar(officer) {
    var lg = lang();
    return '<div class="tbar"><div class="tbar-left"><div class="tbar-icon">MX</div><span class="tbar-name">' + t('app_name') + '</span>' +
      '<span class="tbar-mode">— ' + t(officer ? 'mode_officer' : 'mode_publisher') + '</span></div>' +
      '<div class="tbar-right"><div class="langsw" role="group" aria-label="Language">' +
        '<button data-act="lang" data-arg="ms" class="' + (lg === 'ms' ? 'on' : '') + '" aria-pressed="' + (lg === 'ms') + '">BM</button>' +
        '<button data-act="lang" data-arg="en" class="' + (lg === 'en' ? 'on' : '') + '" aria-pressed="' + (lg === 'en') + '">EN</button></div>' +
        '<div class="tbar-ctl" aria-hidden="true">—</div><div class="tbar-ctl" aria-hidden="true">▢</div><div class="tbar-ctl close" aria-hidden="true">✕</div></div></div>';
  }

  function navItems(officer) {
    var pendingN = 0; try { pendingN = (MX.publisher.pending() || []).length; } catch (e) { }
    var updN = 0; try { updN = (MX.packs.checkUpdates() || []).length; } catch (e) { }
    return officer
      ? [{ k: 'ask', l: 'nav_ask' }, { k: 'library', l: 'nav_library' }, { k: 'updates', l: 'nav_updates', badge: updN }]
      : [{ k: 'verify', l: 'nav_verify', badge: pendingN }, { k: 'build', l: 'nav_build' }, { k: 'eval', l: 'nav_eval' }, { k: 'analytics', l: 'nav_analytics' }];
  }

  function sidebar(officer) {
    var u = user();
    var nav = navItems(officer).map(function (n, i) {
      return '<button data-act="screen" data-arg="' + n.k + '" class="' + (S.screen === n.k ? 'on' : '') + '" aria-current="' + (S.screen === n.k ? 'page' : 'false') + '">' +
        '<span class="nav-key">' + (i + 1) + '</span><span class="nav-label">' + t(n.l) + '</span>' + (n.badge ? '<span class="nav-badge">' + n.badge + '</span>' : '') + '</button>';
    }).join('');
    var menu = '';
    if (S.profileMenu) {
      menu = '<div class="pmenu" data-keep="1"><div class="pmenu-head">' + t('switch_officer') + '</div>' +
        (MX.data.users || []).map(function (p) {
          return '<button class="pmenu-item ' + (p.user_id === u.user_id ? 'on' : '') + '" data-act="user" data-arg="' + esc(p.user_id) + '">' +
            '<div class="avatar">' + esc(initials(p)) + '</div><div style="flex:1"><div class="pmenu-name">' + esc(p.name) + '</div>' +
            '<div class="pmenu-sub">' + esc(roleLine(p)) + '</div><div class="pmenu-sub">' + esc(jurLabel(p.jurisdiction)) + ' · ' + t('clearance') + ' ' + tierLabel(p.clearance_level) + '</div></div></button>';
        }).join('') + '<div class="pmenu-note">' + t('sso_note') + '</div></div>';
    }
    return '<aside class="side"><div class="brand"><div class="brand-name">MixUp</div><div class="brand-sub">Navigator</div></div>' +
      '<div class="modesw" role="group"><button data-act="mode" data-arg="officer" class="' + (officer ? 'on' : '') + '">' + t('officer') + '</button>' +
      '<button data-act="mode" data-arg="publisher" class="' + (!officer ? 'on' : '') + '">' + t('publisher') + '</button></div>' +
      '<nav class="nav">' + nav + '</nav><div class="side-spacer"></div>' +
      '<div class="offline"><div class="offline-title"><span class="offline-dot"></span>' + t('offline') + '</div><div class="offline-text">' + t('offline_text') + '</div></div>' +
      '<div class="side-foot"><span title="Synthetic corpus - sample only">' + t('synthetic') + '</span><button data-act="reset">' + t('reset_demo') + '</button></div>' +
      '<button class="profile" data-act="profile" aria-expanded="' + S.profileMenu + '"><div class="avatar">' + esc(initials(u)) + '</div><div class="profile-text"><div class="profile-name">' + esc(u.name) + '</div>' +
      '<div class="profile-sub">' + esc(jurLabel(u.jurisdiction)) + ' · ' + tierLabel(u.clearance_level) + '</div></div><span class="profile-caret">▲</span></button>' + menu + '</aside>';
  }
  function roleLine(p) {
    var parts = [];
    if (p.scheme || p.grade) parts.push([p.scheme, p.grade].filter(Boolean).join(', '));
    if (p.role && p.role !== 'OFFICER') parts.push(t('role_' + p.role));
    return parts.join(' · ') || t('role_OFFICER');
  }

  function screenMeta() { var k = S.screen; return [t('t_' + k), t('s_' + k)]; }
  function header() {
    var u = user(), m = screenMeta(), unread = 0;
    try { unread = (MX.notifications() || []).filter(function (n) { return !n.read; }).length; } catch (e) { }
    return '<header class="hdr"><div class="hdr-titles"><div class="hdr-title">' + esc(m[0]) + '</div><div class="hdr-sub">' + esc(m[1]) + '</div></div>' +
      '<div class="hdr-right"><div class="pill"><span class="k">' + t('jurisdiction') + '</span><span class="v">' + esc(jurLabel(u.jurisdiction)) + '</span></div>' +
      '<button class="pill-btn" data-act="notif" aria-expanded="' + S.notifOpen + '">' + t('notifications') + (unread ? '<span class="unread">' + unread + '</span>' : '') + '</button></div></header>';
  }
  function notifPopover() {
    if (!S.notifOpen) return '';
    var list = []; try { list = MX.notifications() || []; } catch (e) { }
    var kindClass = { NEW_DOCUMENT: 'k-new', NEW_CIRCULAR: 'k-new', STATUS_CHANGED: 'k-status', STATUS_CHANGE: 'k-status', NEW_RELATION: 'k-rel', UPDATE_AVAILABLE: 'k-upd', INSTALL_FAILED: 'k-fail', INSTALLED: 'k-rel' };
    var items = list.length ? list.map(function (n) {
      var kind = String(n.kind || n.type || '').toUpperCase();
      var kl = L['k_' + { NEW_DOCUMENT: 'new', NEW_CIRCULAR: 'new', STATUS_CHANGED: 'status', STATUS_CHANGE: 'status', NEW_RELATION: 'rel', UPDATE_AVAILABLE: 'upd', INSTALL_FAILED: 'fail', INSTALLED: 'rel' }[kind]] ? t('k_' + { NEW_DOCUMENT: 'new', NEW_CIRCULAR: 'new', STATUS_CHANGED: 'status', STATUS_CHANGE: 'status', NEW_RELATION: 'rel', UPDATE_AVAILABLE: 'upd', INSTALL_FAILED: 'fail', INSTALLED: 'rel' }[kind]) : (bi(n, 'kind_label') || kind);
      return '<button class="npop-item" data-act="notif-open" data-arg="' + esc(n.doc_id || '') + '"><span class="npop-kind ' + (kindClass[kind] || 'k-upd') + '">' + esc(kl) + '</span>' +
        '<span class="npop-title">' + esc(bi(n, 'title')) + '</span><span class="npop-body">' + esc(bi(n, 'body') || bi(n, 'text')) + '</span></button>';
    }).join('') : '<div class="npop-empty">' + t('notif_none') + '</div>';
    return '<div class="npop" data-keep="1"><div class="npop-head"><span class="t">' + t('notifications') + '</span><span class="s">' + t('notif_sub') + '</span></div><div class="npop-list">' + items + '</div></div>';
  }
  function updateEntry() { try { return (MX.packs.checkUpdates() || [])[0] || null; } catch (e) { return null; } }
  function entryChanges(e) {
    var parts = [];
    var nd = pick(e, ['new_documents', 'new_docs', 'added'], null), sc = pick(e, ['status_changes', 'changed'], null);
    if (Array.isArray(nd)) nd = nd.length; if (Array.isArray(sc)) sc = sc.length;
    if (nd != null) parts.push(t('new_circulars', { n: nd }));
    if (sc != null) parts.push(t('status_changes', { n: sc }));
    return parts.length ? parts.join(', ') : (bi(e, 'summary') || t('documents_n', { n: Array.isArray(e.documents) ? e.documents.length : (e.documents || e.doc_count || '?') }));
  }
  function banner(officer) {
    var e = updateEntry();
    if (!officer || !e || S.screen === 'updates') return '';
    return '<div class="banner"><span class="t">' + t('banner_title') + '</span><span class="b">' + esc(t('banner_body', { pack: tierLabel(e.tier), v: e.version, changes: entryChanges(e) })) + '</span>' +
      '<button data-act="screen" data-arg="updates">' + t('banner_btn') + '</button></div>';
  }
  function statusBar() {
    var packs = []; try { packs = MX.packs.installed() || []; } catch (e) { }
    var u = user();
    var line = packs.filter(function (p) { return (p.tier | 0) <= (u.clearance_level | 0); }).map(function (p, i) { return (i ? '' : tierLabel(p.tier) + ' ') + (i ? tierLabel(p.tier) + ' ' : (lang() === 'en' ? 'pack ' : 'pek ')) + 'v' + p.version; }).join(' · ');
    if (lang() === 'ms' && packs.length) line = 'Pek ' + packs.filter(function (p) { return (p.tier | 0) <= (u.clearance_level | 0); }).map(function (p) { return tierLabel(p.tier) + ' v' + p.version; }).join(' · ');
    var stub = '';
    return '<div class="sbar"><span class="net"><span class="dot"></span>' + t('net_offline') + '</span><span>' + t('engine_ready') + '</span><span>' + esc(line) + '</span>' +
      '<span class="spacer"></span><span>' + t('local_note') + esc(stub) + '</span></div>';
  }

  function screen(officer) {
    var k = S.screen;
    if (officer) { if (k === 'library') return libraryScreen(); if (k === 'updates') return updatesScreen(); return askScreen(); }
    if (k === 'build') return buildScreen(); if (k === 'eval') return evalScreen(); if (k === 'analytics') return analyticsScreen();
    return verifyScreen();
  }

  /* ------------------------------------------------------------------ Ask screen */
  function askScreen() {
    var a = S.ask, r = a.result, body;
    if (a.phase === 'idle') {
      body = '<div class="hero"><div class="hero-h">' + t('hero_h') + '</div><div class="hero-p">' + t('hero_p') + '</div><div class="try"><div class="eyebrow">' + t('try') + '</div>' +
        SUGGESTIONS.map(function (sg) { var q = sg[lang()]; return '<button class="sugg" data-act="ask" data-arg="' + esc(q) + '"><span>' + esc(q) + '</span><span class="tag">' + t(sg.tag) + '</span></button>'; }).join('') + '</div></div>';
    } else {
      var final = a.phase === 'final', refused = r && !r.answerable;
      var st = a.phase === 'retrieving' ? t('st_retrieving', { n: (user().clearance_level | 0) + 1 }) : a.phase === 'streaming' ? t('st_streaming', { s: secs(a.sourcesMs) }) : (refused ? t('st_refused') : t('st_final'));
      body = '<div class="qblock"><div class="eyebrow">' + t('question') + '</div><div class="qtext">' + esc(a.question) + '</div></div>' +
        '<div class="statusline ' + (final ? 'final' : '') + (refused ? ' refused' : '') + '"><span class="pdot"></span><span>' + esc(st) + '</span></div>';
      if (r && r.excluded && r.excluded.length) {
        body += '<div class="excluded"><div class="excluded-head"><span class="t">' + t('excluded') + '</span><button class="btn-link" data-act="lineage" data-arg="' + esc(r.excluded[0].doc_id) + '">' + t('view_lineage') + '</button></div>' +
          r.excluded.map(function (x) { return '<div class="excluded-row"><span class="no">' + esc(x.circular_no || docNo(x.doc_id)) + '</span><span class="why">' + esc(x.status_reason) + '</span></div>'; }).join('') + '</div>';
      }
      if (r && a.phase !== 'retrieving') {
        var main = answerCard(r, a, false);
        if (S.compare && a.baseline && final) body += '<div class="compare2">' + main + answerCard(a.baseline, a, true) + '</div>';
        else body += main;
      }
      if (r && final && r.jurisdiction_conflict && r.comparison && r.comparison.mine) body += jurCards(r.comparison);
    }
    var hist = !!MX.state.includeHistorical;
    return '<div class="ask" data-screen-label="Tanya"><div class="ask-left"><div class="ask-scroll" data-scroll="ask"><div class="ask-inner">' + body + '</div></div>' +
      '<div class="composer"><div class="composer-inner"><div class="inputrow"><input id="q" data-act="draft" value="' + esc(S.draft) + '" placeholder="' + t('placeholder') + '" aria-label="' + t('question') + '">' +
      '<button class="ask-btn" data-act="ask">' + t('ask_btn') + '</button></div>' +
      '<div class="composer-foot"><div class="toggles"><button class="toggle ' + (hist ? 'on' : '') + '" data-act="hist" role="switch" aria-checked="' + hist + '"><span class="track"><span class="knob"></span></span>' + t('include_hist') + '</button>' +
      '<button class="toggle ' + (S.compare ? 'on' : '') + '" data-act="compare" role="switch" aria-checked="' + S.compare + '"><span class="track"><span class="knob"></span></span>' + t('compare_chatbot') + '</button></div>' +
      '<span>' + t('searching_in', { packs: packLabel() }) + '</span></div></div></div></div>' + askPanel() + '</div>';
  }
  function answerCard(r, a, isBaseline) {
    var final = a.phase === 'final', html;
    if (isBaseline) {
      var stale = (r.citations || []).filter(function (c) { return c.status === 'CANCELLED' || c.status === 'ONE_OFF'; });
      html = r.answer_html || '';
      stale.forEach(function (c) { html = html.split('data-id="' + c.id + '"').join('data-id="' + c.id + '" data-src="b" class="cite stale"').replace('class="cite" data-id="' + c.id + '" data-src="b" class="cite stale"', 'class="cite stale" data-id="' + c.id + '" data-src="b"'); });
      html = html.replace(/<span class="cite" data-id="(S\d+)">/g, '<span class="cite" data-id="$1" data-src="b">');
      var head = '<span class="eyebrow">' + t('typical') + '</span><span class="r">' + (stale.length ? '<span class="tag-wrong">' + t('wrong') + '</span><span class="muted" style="font-size:11px">' + t('wrong_why') + '</span>' : '') + '</span>';
      var cites = (r.citations || []).map(function (c) { return '<span class="row"><span class="src-id">' + esc(c.id) + '</span><span class="mono" style="font-weight:600">' + esc(c.circular_no) + '</span>' + statusChip(c.status) + '</span>'; }).join('');
      return '<div class="answer baseline"><div class="answer-head">' + head + '</div><p class="atext">' + (r.answerable ? html : esc(stripTags(html))) + '</p>' +
        '<div class="baseline-cites"><span>' + t('baseline_note') + '</span>' + cites + '</div></div>';
    }
    var tokens = tokenizeAnswer(r.answer_html || '');
    html = (final ? tokens.join('') : tokens.slice(0, a.shown).join('') + '<span class="caret"></span>');
    var conf = r.confidence ? '<span class="chip-conf conf-' + esc(r.confidence) + '">' + t('confidence') + ': ' + t('conf_' + r.confidence) + '</span>' : '';
    var foot = final ? '<div class="answer-foot"><span class="timing">' + esc(t('timing', { a: secs(a.sourcesMs), b: secs(a.completeMs) })) + '</span><div class="fb">' +
      '<button data-act="fb" data-arg="up" class="' + (a.feedback === 'up' ? 'on' : '') + '">' + t('helpful') + '</button><button data-act="fb" data-arg="down" class="' + (a.feedback === 'down' ? 'on' : '') + '">' + t('not_helpful') + '</button></div></div>' : '';
    return '<div class="answer"><div class="answer-head"><span class="eyebrow">' + (r.answerable ? t('answer') : t('cannot_answer')) + '</span>' + (r.answerable && final ? conf : '') + '</div>' +
      '<p class="atext" id="atext">' + html + '</p>' + foot + '</div>';
  }
  function stripTags(h) { return String(h).replace(/<[^>]+>/g, ''); }
  function tokenizeAnswer(html) { // keep tags and [S#] chips whole; split text by words so the answer can "stream"
    var out = [], parts = String(html).split(/(<span class="cite"[^>]*>[\s\S]*?<\/span>|<[^>]+>)/);
    parts.forEach(function (p, i) { if (!p) return; if (i % 2 === 1) out.push(p); else (p.match(/\S+\s*|\s+/g) || []).forEach(function (w) { out.push(w); }); });
    return out;
  }
  function jurCards(cmp) {
    function card(c, mine) {
      if (!c) return '';
      return '<div class="jur-card ' + (mine ? 'mine' : '') + '"><div class="top"><span class="l">' + esc(jurLabel(c.jurisdiction)) + '</span><span class="r">' + t(mine ? 'your_rule' : 'comparison') + '</span></div>' +
        '<div class="rule">' + esc(keyFigure(c.text) || c.clause_ref || '') + '</div><div class="detail">' + esc(firstSentence(c.text)) + '</div><div class="doc">' + esc(c.circular_no) + ' · ' + esc(c.clause_ref || '') + '</div></div>';
    }
    return '<div class="jur"><div class="jur-head"><span class="t">' + t('jur_differs') + '</span><span class="s">' + t('jur_first') + '</span></div><div class="jur-grid">' + card(cmp.mine, true) + card(cmp.other, false) + '</div></div>';
  }

  /* Right panel of the Ask screen: Sources | Page | Lineage */
  function askPanel() {
    var a = S.ask, r = a.result, ready = r && a.phase !== 'retrieving';
    var n = ready && r.citations ? r.citations.length : 0;
    var tabs = [['sources', t('tab_sources') + (n ? ' (' + n + ')' : '')], ['viewer', t('tab_page')], ['lineage', t('tab_lineage')]];
    var body;
    if (!ready) body = '<div class="empty">' + t(a.phase === 'retrieving' ? 'empty_retrieving' : 'empty_idle') + '</div>';
    else if (S.tab === 'viewer') body = S.viewer ? viewerHtml(S.viewer, 'viewer') : '<div class="empty">' + t('empty_page') + '</div>';
    else if (S.tab === 'lineage') body = S.lineageDoc ? lineageHtml(S.lineageDoc, 'lineage', r.citations && r.citations[0] && r.citations[0].doc_id) : '<div class="empty">' + t('empty_lineage') + '</div>';
    else body = n ? sourcesHtml(r.citations) : '<div class="empty">' + t(r.answerable ? 'empty_idle' : 'empty_refused') + '</div>';
    return panelHtml(tabs, S.tab, 'tab', body, 'askpanel');
  }
  function panelHtml(tabs, active, act, body, scrollKey) {
    return '<div class="panel"><div class="tabs" role="tablist">' + tabs.map(function (tb) {
      return '<button role="tab" aria-selected="' + (active === tb[0]) + '" data-act="' + act + '" data-arg="' + tb[0] + '" class="' + (active === tb[0] ? 'on' : '') + '">' + esc(tb[1]) + '</button>';
    }).join('') + '</div><div class="panel-body" data-scroll="' + scrollKey + '">' + body + '</div></div>';
  }
  function sourcesHtml(cites) {
    return '<div class="srcs">' + cites.map(function (c) {
      var hist = c.status === 'CANCELLED' || c.status === 'ONE_OFF';
      var sel = S.viewer && S.viewer.cite === c.id;
      return '<div class="src ' + (hist ? 'hist' : '') + (sel ? ' sel' : '') + '" id="src-' + esc(c.id) + '"><div class="src-top"><span class="src-id">' + esc(c.id) + '</span><span class="src-no">' + esc(c.circular_no) + '</span><span style="flex:1"></span>' + statusChip(c.status) + '</div>' +
        '<div class="src-title">' + esc(c.title) + '</div><div class="src-crumb">' + esc(c.breadcrumb || c.clause_ref || '') + ' · ' + t('p_abbr') + ' ' + esc(c.page_no) + ' · ' + esc(jurLabel(c.jurisdiction)) + '</div>' +
        '<div class="src-text">“' + esc(clamp(c.text, 320)) + '”</div><div class="src-foot"><span class="reason">' + esc(c.status_reason || '') + '</span>' +
        '<button class="btn-link" data-act="cite" data-arg="' + esc(c.id) + '">' + t('open_page') + '</button></div></div>';
    }).join('') + '</div>';
  }
  function viewerHtml(v, act) {
    var doc = MX.document(v.doc_id);
    if (!doc) return '<div class="empty">' + t('empty_page') + '</div>';
    var pages = doc.pages || [], idx = Math.max(0, Math.min(pages.length - 1, (v.page_no | 0) - 1)), pg = pages[idx] || { page_no: 1, text: '', heading: '' };
    var hl = (v.hl || '').replace(/\s+/g, ' ').trim().toLowerCase().slice(0, 80);
    var paras = String(pg.text || '').split(/\n+/).map(function (ln) { return ln.trim(); }).filter(function (ln) { return ln && !/SINTETIK\s*[-–]\s*CONTOH/i.test(ln); });
    var rows = paras.map(function (ln) {
      var h = /^#+\s*(.*)$/.exec(ln); if (h) return '<div class="paper-heading">' + esc(h[1]) + '</div>';
      var m = /^(\d+(?:\.\d+)*)[.)]?\s+(.*)$/.exec(ln), txt = m ? m[2] : ln;
      var hit = hl && (txt.toLowerCase().replace(/\s+/g, ' ').indexOf(hl) >= 0 || hl.indexOf(txt.toLowerCase().slice(0, 60)) >= 0);
      return '<div class="para ' + (m ? '' : 'plain') + (hit ? ' hl' : '') + '">' + (m ? '<span class="n">' + esc(m[1]) + '</span>' : '') + '<span>' + esc(txt) + '</span></div>';
    }).join('');
    var clause = v.clause ? ' · ' + esc(v.clause) : '';
    return '<div class="viewer"><div class="viewer-head"><span class="d">' + esc(doc.circular_no || doc.doc_id) + clause + '</span><span class="p">' + esc(t('page_of', { a: idx + 1, b: pages.length })) + '</span>' +
      '<div class="viewer-nav"><button data-act="' + act + '-page" data-arg="' + idx + '" ' + (idx <= 0 ? 'disabled' : '') + ' aria-label="previous page">‹</button><button data-act="' + act + '-page" data-arg="' + (idx + 2) + '" ' + (idx >= pages.length - 1 ? 'disabled' : '') + ' aria-label="next page">›</button></div></div>' +
      '<div class="paper-doc"><div class="paper-issuer">' + esc(doc.issuer || '') + '</div><div class="paper-title">' + esc(doc.circular_no || '') + ' · ' + esc(doc.title || '') + '</div><div class="paper-rule"></div>' +
      (pg.heading ? '<div class="paper-heading">' + esc(pg.heading) + '</div>' : '') + rows + '<div class="paper-spacer"></div><div class="paper-wm">' + t('synthetic') + '</div><div class="paper-foot">' + (idx + 1) + '</div></div></div>';
  }
  function lineageHtml(docId, act, curId) {
    var lg; try { lg = MX.lineage(docId); } catch (e) { lg = null; }
    curId = curId || docId;
    if (!lg || !lg.nodes || !lg.nodes.length) return '<div class="empty">' + t('empty_lineage') + '</div>';
    var nodes = lg.nodes, edges = lg.edges || [];
    var html = '<div class="lineage"><div class="lineage-intro">' + t('lineage_intro') + '</div>';
    nodes.forEach(function (n, i) {
      var prevIds = nodes.slice(0, i).map(function (p) { return p.doc_id; });
      var e = edges.filter(function (ed) { return ed.source === n.doc_id && prevIds.indexOf(ed.target) >= 0; }).sort(function (x, y) { return prevIds.indexOf(y.target) - prevIds.indexOf(x.target); })[0];
      if (e && !n.hidden) {
        var wc = null; try { wc = MX.whatChanged(e.target, e.source); } catch (err) { }
        var summary = wc ? (lang() === 'en' ? wc.summary_en : wc.summary_ms) : '';
        html += '<div class="ln-rel"><div class="bar"><div></div></div><div class="body"><span class="lab">' + esc(relLabel(e.type)) + ' ' + esc(docNo(e.target)) + '</span>' +
          (e.evidence ? '<span class="ev">“' + esc(clamp(e.evidence, 220)) + '” <span class="ref">' + esc(n.circular_no) + (e.page ? ' · ' + t('p_abbr') + ' ' + esc(e.page) : '') + '</span></span>' : '') +
          (summary ? '<div class="chg"><b>' + t('what_changed') + '</b>' + esc(summary) + '</div>' : '') + '</div></div>';
      } else if (i > 0) html += '<div class="ln-rel"><div class="bar"><div></div></div><div class="body" style="padding:6px 0"></div></div>';
      if (n.hidden) {
        html += '<div class="ln-node"><div class="dotcol"><div class="dot dot-UNKNOWN"></div></div><div class="ln-card hidden">' + t('hidden_doc') + '</div></div>';
      } else {
        html += '<div class="ln-node"><div class="dotcol"><div class="dot dot-' + esc(n.status || 'UNKNOWN') + '"></div></div><div class="ln-card ' + (n.doc_id === docId ? 'cur' : '') + '">' +
          '<div class="top"><span class="no">' + esc(n.circular_no) + '</span><span class="date">' + esc(fmtDate(n.date)) + '</span>' + statusChip(n.status) + '</div>' +
          '<div class="title">' + esc(n.title) + '</div><div class="rule">' + esc(jurLabel(n.jurisdiction)) + (n.status_reason ? ' · ' + esc(n.status_reason) : '') + '</div>' +
          '<div class="open"><button class="btn-link" data-act="' + act + '-open" data-arg="' + esc(n.doc_id) + '">' + t('open_page') + '</button></div></div></div>';
      }
    });
    return html + '</div>';
  }

  /* ------------------------------------------------------------------ Library (Officer) */
  function libraryScreen() {
    var u = user(), f = S.lib, rows = [];
    try { rows = MX.library({ status: f.status, jurisdiction: f.jur }) || []; } catch (e) { }
    rows = rows.filter(function (r) { // client-side guard even if the engine already filtered
      if (f.status === 'valid' && (r.status === 'CANCELLED' || r.status === 'ONE_OFF')) return false;
      if (f.status === 'cancelled' && !(r.status === 'CANCELLED' || r.status === 'ONE_OFF')) return false;
      if (f.jur !== 'all' && r.jurisdiction !== f.jur && r.jurisdiction !== 'FEDERAL_SARAWAK') return false;
      return true;
    });
    function chip(group, key, label) { var on = f[group] === key; return '<button class="chipbtn ' + (on ? 'on' : '') + '" data-act="libf" data-arg="' + group + ':' + key + '" aria-pressed="' + on + '">' + esc(label) + '</button>'; }
    var chips = '<div class="chiprow">' + chip('status', 'all', t('f_all')) + chip('status', 'valid', t('f_valid')) + chip('status', 'cancelled', t('f_cancelled')) + '<span class="chipsep"></span>' +
      chip('jur', 'all', t('f_all')) + chip('jur', 'FEDERAL', t('FEDERAL')) + chip('jur', 'SARAWAK', t('SARAWAK')) + '</div>';
    var table = '<div class="table"><div class="lib-head"><span>' + t('col_no') + '</span><span>' + t('col_title') + '</span><span class="col-jur">' + t('col_jur') + '</span><span>' + t('col_status') + '</span><span>' + t('col_date') + '</span><span class="col-tier">' + t('col_tier') + '</span></div>' +
      (rows.length ? rows.map(function (r) {
        var tier = r.tier | 0;
        return '<button class="lib-row ' + (tier ? 'restricted' : '') + (f.doc === r.doc_id ? ' sel' : '') + '" data-act="librow" data-arg="' + esc(r.doc_id) + '"><span class="no">' + esc(r.no || r.circular_no) + '</span>' +
          '<div class="tt"><span class="t">' + esc(r.title) + '</span>' + (r.status_reason ? '<span class="r">' + esc(r.status_reason) + '</span>' : '') + '<span class="sub">' + esc(jurLabel(r.jurisdiction)) + ' \u00b7 ' + tierLabel(tier) + '</span></div><span class="jur col-jur">' + esc(jurLabel(r.jurisdiction)) + '</span>' +
          '<span>' + statusChip(r.status) + '</span><span class="date">' + esc(fmtDate(r.date)) + '</span><span class="tier col-tier ' + (tier ? 'restricted' : '') + '">' + tierLabel(tier) + '</span></button>';
      }).join('') : '<div class="lib-empty">' + t('lib_empty') + '</div>') + '</div>';
    var foot = '<div class="lib-foot">' + t('lib_count', { n: rows.length }) + ' · ' + t((u.clearance_level | 0) >= 1 ? 'lib_foot_t1' : 'lib_foot_t0') + '</div>';
    var panel = '';
    if (f.doc) {
      var body = f.tab === 'lineage' ? lineageHtml(f.doc, 'lib') : viewerHtml(f.viewer || { doc_id: f.doc, page_no: 1 }, 'lib');
      panel = panelHtml([['viewer', t('tab_page')], ['lineage', t('tab_lineage')]], f.tab, 'libtab', body, 'libpanel');
    }
    return '<div class="lib-wrap ' + (f.doc ? 'with-panel' : '') + '" data-screen-label="Pekeliling"><div class="lib" data-scroll="lib">' + chips + table + foot + '</div>' + panel + '</div>';
  }

  /* ------------------------------------------------------------------ Updates (Officer) */
  function defaultSteps(entry) {
    var v = entry ? entry.version : '?', prev = installedVersion(entry ? entry.tier : 0);
    var file = entry ? (entry.file || 'pack-' + tierLabel(entry.tier).toLowerCase() + '-v' + v + '.json') : 'pack.json';
    return [
      { label: t('step1'), detail: 'v' + v + (lang() === 'en' ? ' available · v' : ' tersedia · v') + prev + (lang() === 'en' ? ' installed' : ' dipasang') },
      { label: t('step2').replace(lang() === 'en' ? 'pack file' : 'fail pek', file), detail: entry && entry.size_bytes ? fmtBytes(entry.size_bytes) : (entry && entry.size ? String(entry.size) : '') },
      { label: t('step3'), detail: entry && entry.sha256 ? prefix(entry.sha256) : '' },
      { label: t('step4'), detail: lang() === 'en' ? 'publisher public key' : 'kunci awam penerbit' },
      { label: t('step5'), detail: lang() === 'en' ? 'none required = none' : 'tiada diperlukan = tiada' },
      { label: t('step6'), detail: 'v' + prev + (lang() === 'en' ? ' kept for rollback' : ' disimpan untuk rollback') },
      { label: t('step7') + ' v' + prev + ' → v' + v, detail: '' }
    ];
  }
  function installedVersion(tier) {
    var list = []; try { list = MX.packs.installed() || []; } catch (e) { }
    var p = list.filter(function (x) { return (x.tier | 0) === (tier | 0); })[0];
    return p ? p.version : 0;
  }
  function updatesScreen() {
    var u = user(), U = S.upd, entry = updateEntry();
    var steps = U.steps ? U.steps.map(function (s) { return { label: lang() === 'en' ? (s.label_en || s.label_ms || s.key) : (s.label_ms || s.label_en || s.key), detail: s.detail || '', ok: s.ok }; }) : defaultSteps(entry);
    var stepsHtml = steps.map(function (s, i) {
      var cls = '', mark = '○';
      if (U.steps) { if (i < U.shown) { if (s.ok === false) { cls = 'failed'; mark = '✕'; } else { cls = 'done'; mark = '✓'; } } else if (i === U.shown && U.running) { cls = 'active'; mark = '•'; } }
      return '<div class="step ' + cls + '"><span class="mark">' + mark + '</span><span>' + esc(s.label) + '</span><span class="detail">' + esc(s.detail) + '</span></div>';
    }).join('');
    var right = '';
    if (U.result && !U.running) {
      if (U.result.ok) right = '<span class="installed-chip">' + t('installed_active', { v: U.lastTarget ? U.lastTarget.version : '' }) + '</span>';
      else right = '<span class="failed-chip">' + t('rejected_chip', { v: installedVersion(U.lastTarget ? U.lastTarget.tier : 0) }) + '</span>';
    }
    if (entry && !U.running) {
      right += '<button class="btn-secondary" data-act="install" data-arg="tamper">' + t('tamper_btn') + '</button>' +
        '<button class="btn-primary" data-act="install">' + t('install_btn', { pack: tierLabel(entry.tier), v: entry.version }) + '</button>';
    } else if (!entry && !U.result) right = '<span class="muted" style="font-size:12px">' + t('no_update') + '</span>';
    var fail = (U.result && !U.result.ok && !U.running && U.shown >= steps.length) ? '<div class="upd-fail">' + esc(bi(U.result, 'reason') || U.result.reason || '') + '</div>' : '';
    var card = '<div class="upd-card"><div class="upd-top"><div class="l"><span class="eyebrow">' + t('channel') + '</span><span class="path">' + esc(CHANNEL_PATH) + '</span></div><div class="r">' + right + '</div></div>' +
      '<div class="steps">' + stepsHtml + '</div>' + fail + '<div class="upd-note">' + t('upd_note') + '</div></div>';
    var changed = '';
    if (U.result && U.result.ok && !U.running && U.lastTarget) {
      var d = U.result.diff || {}, items = [];
      (d.added || []).forEach(function (x) { var doc = typeof x === 'string' ? docById(x) : x; var no = doc ? (doc.circular_no || doc.doc_id) : String(x);
        items.push(['k-new', t('k_new'), no + (doc && doc.title ? ' · ' + doc.title : ''), doc && doc.effective_date ? t('in_force_from', { d: fmtDate(doc.effective_date) }) : '']); });
      (d.status_changes || []).forEach(function (x) { var no = x.circular_no || docNo(x.doc_id), from = x.from || x.old || x.old_status, to = x.to || x['new'] || x.new_status;
        items.push(['k-status', t('k_status'), no + ' · ' + t(from) + ' → ' + t(to), x.reason || x.status_reason || bi(x, 'reason') || '']); });
      (d.relations || d.new_relations || []).forEach(function (x) { items.push(['k-rel', t('k_rel'), docNo(x.source_doc_id || x.source) + ' ' + relLabel(x.relation_type || x.type).toLowerCase() + ' ' + docNo(x.target_doc_id || x.target), x.evidence_text || x.evidence || '']); });
      changed = '<div class="upd-card"><div class="changes-head"><span class="t">' + esc(t('changed_title', { a: U.prevVersion, b: U.lastTarget.version })) + '</span><span class="s">' + t('changed_sub') + '</span></div>' +
        (items.length ? items.map(function (it) { return '<div class="change"><span class="kind ' + it[0] + '">' + esc(it[1]) + '</span><div class="body"><span class="t">' + esc(it[2]) + '</span><span class="b">' + esc(it[3]) + '</span></div></div>'; }).join('')
          : '<div class="change"><span class="kind k-rel">—</span><div class="body"><span class="b">' + esc(bi(U.result, 'summary') || '') + '</span></div></div>') + '</div>';
    }
    var packs = []; try { packs = (MX.packs.installed() || []).filter(function (p) { return (p.tier | 0) <= (u.clearance_level | 0); }); } catch (e) { }
    var packCards = packs.map(function (p) {
      var docs = Array.isArray(p.documents) ? p.documents.length : pick(p, ['documents', 'doc_count', 'document_count'], '?');
      var meta = (p.file || 'pack-' + tierLabel(p.tier).toLowerCase() + '-v' + p.version + '.json') + '<br>' + esc(t('documents_n', { n: docs })) + ' · ' + t('in_browser_index') + (p.size_bytes ? ' · ' + fmtBytes(p.size_bytes) : '') + (p.sha256 ? '<br>sha256 ' + esc(prefix(p.sha256, 8)) : '');
      var note = (p.tier | 0) >= 1 ? t('opened_terhad', { t: tierLabel(u.clearance_level) }) : t('installed_on', { d: fmtDate(p.installed_at || p.installed || p.built_at) }) + (p.previous_version ? ' · ' + t('kept_rollback', { v: p.previous_version }) : '');
      return '<div class="pack"><div class="top"><span class="n">' + esc(tierLabel(p.tier)) + (lang() === 'en' ? ' pack' : '') + '</span><span class="v">v' + esc(p.version) + '</span></div><div class="meta">' + meta + '</div><div class="note">' + esc(note) + '</div></div>';
    }).join('');
    if ((u.clearance_level | 0) < 1) packCards += '<div class="pack-locked">' + t('pack_locked') + '</div>';
    return '<div class="updates" data-screen-label="Kemas kini" data-scroll="upd"><div class="col">' + card + changed + '</div><div class="packs"><div class="eyebrow">' + t('installed_packs') + '</div>' + packCards + '</div></div>';
  }
  function runInstall(tamper) {
    var U = S.upd, entry = updateEntry(); if (!entry || U.running) return;
    U.running = true; U.steps = null; U.shown = -1; U.result = null; U.tamper = !!tamper; U.lastTarget = entry; U.prevVersion = installedVersion(entry.tier);
    render();
    Promise.resolve(MX.packs.install(entry, { tamper: !!tamper })).then(function (res) {
      U.steps = res.steps || []; U.result = res; U.shown = 0;
      var i = 0;
      (function tick() {
        render();
        if (i >= U.steps.length) { U.running = false; render(); return; }
        var step = U.steps[i];
        later(function () { i++; U.shown = i; if (step.ok === false) { U.running = false; U.shown = U.steps.length; } tick(); }, 650);
      })();
    }).catch(function (err) { U.running = false; U.result = { ok: false, reason: String(err) }; U.steps = []; U.shown = 0; render(); });
  }

  /* ------------------------------------------------------------------ Publisher: Circulars (upload + verification queue) */
  function verifyScreen() {
    var P = S.pub, html = '<div class="pub" data-screen-label="Pengesahan" data-scroll="pub"><div class="pub-intro">' + t('pub_intro') + '</div>';
    html += '<div class="upload"><div class="l"><span class="t">' + t('upload_t') + '</span><span class="s">' + t('upload_s') + '</span>' + (P.committed ? '<span class="decided ok">' + esc(t('added_msg', { no: P.committed })) + '</span>' : '') + '</div>' +
      '<div class="r"><label class="btn-secondary filebtn">' + t('choose_file') + '<input type="file" accept=".md,.txt,text/plain,text/markdown" data-act="file" aria-label="' + t('choose_file') + '"></label>' +
      '<button class="btn-primary" data-act="demo-upload">' + t('demo_upload') + '</button></div></div>';
    if (P.analysis) {
      var A = P.analysis, m = A.meta || {};
      var metaRows = [['m_no', m.circular_no], ['m_title', m.title], ['m_issuer', m.issuer], ['m_type', m.doc_type ? t(m.doc_type) : ''], ['m_issued', fmtDate(m.issue_date)], ['m_effective', fmtDate(m.effective_date)],
        ['m_class', tierLabel(m.classification_level)], ['m_jur', jurLabel(m.jurisdiction)], ['m_pages', (A.pages || []).length || m.page_count || '']];
      var cands = A.candidates || [];
      html += '<div class="analysis"><div class="eyebrow">' + t('analysis_t') + ' · ' + esc(P.filename) + '</div><div class="meta-grid">' + metaRows.map(function (r) { return '<div><div class="k">' + t(r[0]) + '</div><div class="v">' + esc(r[1] || '—') + '</div></div>'; }).join('') + '</div>' +
        '<div class="eyebrow">' + t('relations_found', { n: cands.length }) + '</div>' + (cands.length ? cands.map(function (c) {
          return '<div class="cand"><div class="top"><span class="no">' + esc(m.circular_no || '') + '</span><span class="rel-tag">' + esc(relLabel(c.relation_type)) + '</span><span class="no">' + esc(c.target_doc_id ? docNo(c.target_doc_id) : c.target_ref_text) + '</span>' +
            (!c.target_doc_id ? '<span class="muted" style="font-size:12px">' + esc(c.target_ref_text || '') + '</span>' : '') + '</div><div class="ev">“' + esc(clamp(c.evidence_text, 260)) + '”</div>' +
            '<div class="where">' + t('p_abbr') + ' ' + esc(c.evidence_page) + ' · ' + t('extraction_conf').toLowerCase() + ' ' + esc(Number(c.confidence || 0).toFixed(2)) + '</div></div>';
        }).join('') : '<div class="muted" style="font-size:13px">' + t('no_relations') + '</div>') +
        '<div style="display:flex;gap:8px"><button class="btn-primary" data-act="commit">' + t('add_library') + '</button><button class="btn-secondary" data-act="discard">' + t('discard') + '</button></div></div>';
    }
    var pending = []; try { pending = MX.publisher.pending() || []; } catch (e) { }
    var decidedIds = Object.keys(P.decided);
    var items = pending.filter(function (c) { return !P.decided[c.relation_id]; }).map(function (c) { return vItem(c, null); }).join('') +
      decidedIds.map(function (id) { return vItem(P.decided[id].item, P.decided[id].decision); }).join('');
    html += '<div class="pub-section">' + t('queue_t') + '</div>' + (items || '<div class="queue-empty">' + t('queue_empty') + '</div>') + '</div>';
    return html;
  }
  function vItem(c, decision) {
    var src = docById(c.source_doc_id), tgt = c.target_doc_id ? docById(c.target_doc_id) : null;
    var effect = c.relation_type === 'AMENDS' ? docNo(c.target_doc_id) + ' → ' + t('AMENDED') : (c.relation_type === 'CANCELS' || c.relation_type === 'SUPERSEDES') ? docNo(c.target_doc_id) + ' → ' + t('CANCELLED') : t('no_effect');
    var right = decision ? '<div class="decided ' + (decision === 'approved' ? 'ok' : 'no') + '">' + t(decision === 'approved' ? 'dec_ok' : 'dec_no') + '</div>'
      : '<button class="btn-primary" data-act="verify" data-arg="' + esc(c.relation_id) + ':1">' + t('verify') + '</button><button class="btn-secondary" data-act="verify" data-arg="' + esc(c.relation_id) + ':0">' + t('reject') + '</button>';
    return '<div class="vitem ' + (decision === 'rejected' ? 'rejected' : '') + '"><div class="l"><div class="top"><span class="no">' + esc(src ? src.circular_no : c.source_doc_id) + '</span><span class="rel-tag">' + esc(relLabel(c.relation_type)) + '</span>' +
      '<span class="no">' + esc(tgt ? tgt.circular_no : (c.target_ref_text || c.target_doc_id || '?')) + '</span><span class="jur">' + esc(jurLabel(src ? src.jurisdiction : '')) + '</span></div>' +
      '<div class="ev">“' + esc(clamp(c.evidence_text, 300)) + '”</div><div class="where">' + esc(src ? src.circular_no : '') + ' · ' + t('p_abbr') + ' ' + esc(c.evidence_page) + ' · ' + t('effect') + ': ' + esc(effect) + '</div></div>' +
      '<div class="r"><div class="conf">' + t('extraction_conf') + ' <b>' + esc(Number(c.confidence || 0).toFixed(2)) + '</b></div>' + right + '</div></div>';
  }

  /* ------------------------------------------------------------------ Publisher: Build packs */
  function manifestList() { var m = null; try { m = MX.packs.manifest(); } catch (e) { } if (!m) return []; return Array.isArray(m) ? m : (m.packs || m.entries || m.tiers || []); }
  function manifestVersion() { var m = null; try { m = MX.packs.manifest(); } catch (e) { } var list = manifestList(); return (m && m.version) || Math.max.apply(null, [0].concat(list.map(function (p) { return Number(p.version) || 0; }))); }
  function buildScreen() {
    var B = S.build, list = manifestList(), cur = manifestVersion();
    if (B.version == null) B.version = cur + 1;
    var rels = MX.data.relations || [], verified = rels.filter(function (r) { return r.verified && !r.rejected; }).length;
    var pendingN = 0; try { pendingN = (MX.publisher.pending() || []).length; } catch (e) { }
    var tiers = (list.length ? list : [{ tier: 0, version: cur }, { tier: 1, version: cur }]).map(function (p) {
      var docs = Array.isArray(p.documents) ? p.documents.length : pick(p, ['documents', 'doc_count'], (MX.data.documents || []).filter(function (d) { return (d.classification_level | 0) <= (p.tier | 0); }).length);
      var inst = installedVersion(p.tier);
      return '<div class="tiercard"><div class="l"><div class="nm"><span class="n">' + esc(tierLabel(p.tier)) + (lang() === 'en' ? ' pack' : '') + '</span><span class="tier-chip tier-' + (p.tier | 0) + '">' + esc(tierLabel(p.tier)) + '</span></div>' +
        '<div class="meta">' + esc(t('documents_n', { n: docs })) + ' · ' + esc(t('verified_rel', { n: verified })) + '</div><div class="deliv">' + t('deliver_' + Math.min(2, p.tier | 0)) + '</div></div>' +
        '<div class="ver">' + (inst && inst !== p.version ? 'v' + inst + ' → ' : '') + 'v' + esc(p.version) + '</div></div>';
    }).join('');
    var incl = '<div class="incl"><span class="eyebrow">' + t('included', { v: installedVersion(0) || cur }) + '</span><span class="s">' + esc(t('documents_n', { n: (MX.data.documents || []).length })) + ' · ' + esc(t('verified_rel', { n: verified })) + ' · ' + esc(t('pending_rel', { n: pendingN })) + ' · ' + t('in_browser_index') + '</span></div>';
    var mtable = '';
    if (B.done && list.length) {
      mtable = '<div class="mtable"><div class="mrow head"><span>' + t('c_tier') + '</span><span>' + t('c_ver') + '</span><span>' + t('c_file') + '</span><span>' + t('c_sha') + '</span><span>' + t('c_sig') + '</span><span>' + t('c_docs') + '</span></div>' +
        list.map(function (p) { return '<div class="mrow"><span><span class="tier-chip tier-' + (p.tier | 0) + '">' + esc(tierLabel(p.tier)) + '</span></span><span class="mono">v' + esc(p.version) + '</span><span class="m">' + esc(p.file || '') + '</span><span class="m">' + esc(prefix(p.sha256, 8)) + '</span><span class="m">' + esc(prefix(p.signature, 8)) + '</span><span class="mono">' + esc(Array.isArray(p.documents) ? p.documents.length : (p.documents || p.doc_count || '')) + '</span></div>'; }).join('') + '</div>';
    }
    var stepKeys = ['b1', 'b2', 'b3', 'b4', 'b5', 'b6'];
    var steps = stepKeys.map(function (k, i) { var cls = B.done || i < B.shown ? 'done' : (B.running && i === B.shown ? 'active' : ''); return '<div class="bstep ' + cls + '"><span class="mark">' + (cls === 'done' ? '✓' : cls === 'active' ? '•' : '○') + '</span><span>' + t(k) + '</span></div>'; }).join('');
    var action;
    if (!B.done) action = '<div class="verrow"><span>' + t('version') + '</span><input type="number" min="1" data-act="buildver" value="' + esc(B.version) + '" aria-label="' + t('version') + '"><span style="flex:1"></span></div>' +
      '<button class="btn-amber" data-act="build" ' + (B.running ? 'disabled' : '') + '>' + t('build_btn', { v: B.version }) + '</button>';
    else {
      var first = list[0] || {};
      action = '<div class="sig">sha256 ' + esc(first.sha256 || '') + '<br>sig ' + esc(first.signature || '') + '<br>' + t('sig_note') + '</div>' +
        '<button class="btn-pale ' + (B.published ? 'done' : '') + '" data-act="publish">' + t(B.published ? 'published' : 'publish_btn') + '</button>';
    }
    return '<div class="build" data-screen-label="Bina pek" data-scroll="build"><div class="col" style="gap:12px">' + tiers + incl + mtable + '</div><div class="dark"><div class="t">' + t('build_sign') + '</div><div class="bsteps">' + steps + '</div>' + action + '</div></div>';
  }
  function runBuild() {
    var B = S.build; if (B.running) return;
    B.running = true; B.shown = 0; B.done = false; B.published = false; render();
    var p = Promise.resolve(MX.packs.build(B.version)), i = 0;
    (function tick() { if (i < 5) { later(function () { i++; B.shown = i; render(); tick(); }, 600); } })();
    p.then(function (res) {
      var finish = function () { if (i < 5) { later(finish, 300); return; } B.running = false; B.done = true; B.result = res; B.shown = 6; render(); };
      finish();
    }).catch(function (err) { B.running = false; B.shown = -1; render(); alert(String(err)); });
  }

  /* ------------------------------------------------------------------ Publisher: Evaluation */
  var METRICS = [
    ['correct_current', ['correct_current', 'correct_and_current', 'correct_current_rate', 'correct'], 'm_correct', '-', 'pct', true],
    ['cancelled_citation_rate', ['cancelled_citation_rate', 'cancelled_rate', 'stale_citation_rate'], 'm_cancelled', '≤ 5%', 'pct', false],
    ['recall_at_5', ['recall_at_5', 'recall5', 'recall@5', 'recall'], 'm_recall', '≥ 0.80', 'pct', true],
    ['mrr', ['mrr'], 'm_mrr', '≥ 0.60', 'num', true],
    ['citation_accuracy', ['citation_accuracy'], 'm_cite', '≥ 0.85', 'pct', true],
    ['jurisdiction_accuracy', ['jurisdiction_accuracy'], 'm_jur_acc', '-', 'pct', true],
    ['refusal_accuracy', ['refusal_accuracy'], 'm_refusal', '≥ 0.80', 'pct', true],
    ['false_refusal_rate', ['false_refusal_rate'], 'm_false_refusal', '-', 'pct', false],
    ['access_leaks', ['access_leaks', 'leaks'], 'm_leaks', '0', 'int', false],
    ['latency_p50_ms', ['latency_p50_ms', 'latency_p50', 'p50_ms'], 'm_p50', '≤ 8 s', 'ms', false],
    ['latency_p95_ms', ['latency_p95_ms', 'latency_p95', 'p95_ms'], 'm_p95', '≤ 15 s', 'ms', false]
  ];
  function fmtMetric(v, kind) {
    if (v == null || v === '') return '—';
    if (typeof v === 'string') return v;
    if (kind === 'pct') return Number(v) <= 1 ? pct(v) : Number(v).toFixed(1) + '%';
    if (kind === 'num') return Number(v).toFixed(3);
    if (kind === 'ms') return Number(v) >= 1000 ? (Number(v) / 1000).toFixed(1) + ' s' : Number(v).toFixed(1) + ' ms';
    return String(v);
  }
  function evalScreen() {
    var E = S.evalRes; if (!E) { try { E = MX.evaluation(); } catch (e) { E = null; } S.evalRes = E; }
    E = E || {};
    var base = E.baseline || {}, nav = E.navigator || {};
    var rows;
    if (Array.isArray(E.metrics)) rows = E.metrics.map(function (m) { return [bi(m, 'label') || m.key, m.baseline, m.navigator, m.target || '-', false]; });
    else rows = METRICS.map(function (m) { var b = pick(base, m[1], null), n = pick(nav, m[1], null); if (b == null && n == null) return null;
      var better = (m[5] ? Number(n) >= Number(b) : Number(n) <= Number(b)); return [t(m[2]), fmtMetric(b, m[4]), fmtMetric(n, m[4]), m[3], better]; }).filter(Boolean);
    var table = '<div class="table"><div class="erow head"><span>' + t('metric') + '</span><span>' + t('baseline') + '</span><span>' + t('navigator') + '</span><span>' + t('target') + '</span></div>' +
      rows.map(function (r) { return '<div class="erow"><span>' + esc(r[0]) + '</span><span class="num">' + esc(r[1]) + '</span><span class="num ' + (r[4] ? 'good' : '') + '">' + esc(r[2]) + '</span><span class="num muted">' + esc(r[3]) + '</span></div>'; }).join('') + '</div>';
    var byType = E.by_type || E.per_type || E.types || [];
    if (!Array.isArray(byType)) byType = Object.keys(byType).map(function (k) { var v = byType[k]; return { type: k, n: v.n, baseline: v.baseline, navigator: v.navigator }; });
    var typeTable = byType.length ? '<div><div class="eyebrow" style="margin-bottom:8px">' + t('by_type') + '</div><div class="table"><div class="trow head"><span>' + t('type') + '</span><span>n</span><span>' + t('baseline') + '</span><span>' + t('navigator') + '</span></div>' +
      byType.map(function (r) { return '<div class="trow"><span>' + esc(r.type || r.name) + '</span><span class="num mono">' + esc(r.n) + '</span><span class="num mono">' + esc(r.baseline) + '</span><span class="num mono good">' + esc(r.navigator) + '</span></div>'; }).join('') + '</div></div>' : '';
    var headline = lang() === 'en' ? (E.headline_en || E.headline_ms) : (E.headline_ms || E.headline_en);
    return '<div class="evalw" data-screen-label="Penilaian" data-scroll="eval"><div class="headline"><div class="t">' + esc(headline || '—') + '</div><div class="r"><span class="s">' + t(S.evalSource === 'browser' ? 'src_browser' : 'src_precomputed') + (E.generated_at ? ' · ' + esc(E.generated_at) : '') + (E.n_questions ? ' · ' + esc(E.n_questions) + ' Q' : '') + '</span>' +
      '<button class="btn-primary" data-act="run-eval" ' + (S.evalRunning ? 'disabled' : '') + '>' + t(S.evalRunning ? 'running' : 'run_browser') + '</button></div></div>' + table + typeTable + '</div>';
  }
  function runEval() {
    if (S.evalRunning) return;
    S.evalRunning = true; render();
    later(function () {
      var run = typeof MX.runEvaluation === 'function' ? MX.runEvaluation() : MX.evaluation({ run: true });
      Promise.resolve(run).then(function (res) { S.evalRes = res || S.evalRes; S.evalSource = 'browser'; })
        .catch(function (e) { console.error(e); }).then(function () { S.evalRunning = false; render(); });
    }, 30);
  }

  /* ------------------------------------------------------------------ Publisher: Analytics */
  function analyticsScreen() {
    var A = {}; try { A = MX.analytics() || {}; } catch (e) { }
    var total = pick(A, ['total_queries', 'total', 'count', 'queries'], 0);
    var unans = pick(A, ['unanswered_rate', 'refusal_rate'], null);
    var topQ = pick(A, ['top_questions', 'questions'], []), topX = pick(A, ['top_excluded', 'most_excluded', 'excluded'], []);
    var exclTotal = pick(A, ['excluded_total', 'exclusions'], topX.reduce(function (s, x) { return s + (x.count || x.n || 0); }, 0));
    var users = pick(A, ['active_users', 'users'], null);
    var stats = [[total, 'a_total'], [unans == null ? '—' : (Number(unans) <= 1 ? pct(unans) : unans + '%'), 'a_unanswered'], [exclTotal, 'a_excluded'], [users == null ? '—' : users, 'a_users']];
    function list(title, arr, kkey, ckey) {
      return '<div class="list"><div class="eyebrow">' + t(title) + '</div>' + (arr && arr.length ? arr.slice(0, 8).map(function (x) { return '<div class="row"><span>' + esc(x[kkey] || x.text || x.label || x.question || x.circular_no || x.doc_id) + '</span><span class="c">' + esc(x[ckey] != null ? x[ckey] : (x.n != null ? x.n : '')) + '</span></div>'; }).join('') : '<div class="none">' + t('a_none') + '</div>') + '</div>';
    }
    return '<div class="evalw" data-screen-label="Analitik" data-scroll="ana"><div class="stats">' + stats.map(function (s) { return '<div class="stat"><div class="v">' + esc(s[0]) + '</div><div class="k">' + t(s[1]) + '</div></div>'; }).join('') + '</div>' +
      '<div class="lists">' + list('a_top_q', topQ, 'question', 'count') + list('a_top_ex', topX, 'circular_no', 'count') + '</div></div>';
  }

  /* ------------------------------------------------------------------ Ask flow */
  function ask(q) {
    q = String(q || '').trim(); if (!q) return;
    clearTimers();
    S.draft = ''; S.screen = 'ask'; MX.state.mode = 'officer';
    S.ask = { phase: 'retrieving', question: q, result: null, baseline: null, t0: performance.now(), shown: 0, sourcesMs: 0, completeMs: 0, feedback: null };
    S.tab = 'sources'; S.viewer = null; S.lineageDoc = null;
    render();
    later(function () { // short pause so the "searching" state is visible, then the real (fast) engine call
      var a = S.ask, t1 = performance.now(), res;
      try { res = MX.ask(q, { baseline: false }); } catch (e) { console.error(e); res = { answerable: false, answer_html: esc(String(e)), citations: [], excluded: [], confidence: 'LOW' }; }
      a.sourcesMs = res.timing_ms != null ? res.timing_ms : (performance.now() - t1);
      a.result = res;
      if (S.compare) { try { a.baseline = MX.ask(q, { baseline: true }); } catch (e) { a.baseline = null; } }
      a.lineageAuto = (res.excluded && res.excluded[0] && res.excluded[0].doc_id) || (res.citations && res.citations[0] && res.citations[0].doc_id) || null;
      S.lineageDoc = a.lineageAuto;
      if (res.citations && res.citations[0]) S.viewer = citeViewer(res.citations[0]);
      a.phase = 'streaming'; a.shown = 0; render();
      var tokens = tokenizeAnswer(res.answer_html || ''), speed = 14;
      (function step() {
        a.shown += 1;
        if (a.shown >= tokens.length) { a.phase = 'final'; a.completeMs = performance.now() - a.t0; render(); return; }
        var el = document.getElementById('atext'); if (el) el.innerHTML = tokens.slice(0, a.shown).join('') + '<span class="caret"></span>';
        later(step, speed);
      })();
    }, 350);
  }
  function citeViewer(c) { return { doc_id: c.doc_id, page_no: c.page_no || 1, hl: c.text, clause: c.clause_ref, cite: c.id }; }
  function findCite(id, src) { var a = S.ask, r = src === 'b' ? a.baseline : a.result; return r && (r.citations || []).filter(function (c) { return c.id === id; })[0]; }

  /* ------------------------------------------------------------------ actions (event delegation) */
  var ACT = {
    lang: function (v) { MX.state.lang = v; render(); },
    mode: function (v) { MX.state.mode = v; S.screen = v === 'officer' ? 'ask' : 'verify'; S.profileMenu = S.notifOpen = false; render(); },
    screen: function (v) { S.screen = v; S.profileMenu = S.notifOpen = false; render(); },
    profile: function () { S.profileMenu = !S.profileMenu; S.notifOpen = false; render(); },
    notif: function () { S.notifOpen = !S.notifOpen; S.profileMenu = false; if (S.notifOpen) { try { MX.markRead(); } catch (e) { } } render(); },
    'notif-open': function () { S.notifOpen = false; MX.state.mode = 'officer'; S.screen = 'updates'; render(); },
    user: function (id) {
      MX.setUser(id); S.profileMenu = false; S.lib.doc = null; S.upd = freshState().upd;
      if (S.ask.question) ask(S.ask.question); else render();
    },
    reset: function () { clearTimers(); try { MX.reset(); } catch (e) { console.error(e); } S = freshState(); render(); },
    ask: function (v, el) { ask(v || (document.getElementById('q') || {}).value || S.draft); },
    draft: function (v, el) { S.draft = el.value; },
    hist: function () { MX.state.includeHistorical = !MX.state.includeHistorical; if (S.ask.question) ask(S.ask.question); else render(); },
    compare: function () { S.compare = !S.compare; if (S.ask.question && S.ask.phase === 'final') ask(S.ask.question); else render(); },
    fb: function (v) { S.ask.feedback = v; render(); },
    tab: function (v) { S.tab = v; render(); },
    cite: function (id, el) { var c = findCite(id, el.getAttribute('data-src')); if (c) { S.viewer = citeViewer(c); S.tab = 'viewer'; render(); } },
    lineage: function (docId) { S.lineageDoc = docId || S.lineageDoc; S.tab = 'lineage'; render(); },
    'viewer-page': function (n) { if (S.viewer) { S.viewer.page_no = n | 0; S.viewer.hl = ''; render(); } },
    'lineage-open': function (docId) { S.viewer = { doc_id: docId, page_no: 1 }; S.tab = 'viewer'; render(); },
    libf: function (v) { var p = v.split(':'); S.lib[p[0]] = p[1]; render(); },
    librow: function (docId) { S.lib.doc = docId; S.lib.viewer = { doc_id: docId, page_no: 1 }; S.lib.tab = 'viewer'; render(); },
    libtab: function (v) { S.lib.tab = v; render(); },
    'lib-page': function (n) { if (S.lib.viewer) { S.lib.viewer.page_no = n | 0; render(); } },
    'lib-open': function (docId) { S.lib.viewer = { doc_id: docId, page_no: 1 }; S.lib.tab = 'viewer'; render(); },
    install: function (v) { runInstall(v === 'tamper'); },
    'demo-upload': function () { analyze('SPP-1-2026.md', MX.publisher.demoUploadText()); },
    file: function (v, el) {
      var f = el.files && el.files[0]; if (!f) return;
      var rd = new FileReader(); rd.onload = function () { analyze(f.name, String(rd.result || '')); }; rd.readAsText(f);
    },
    commit: function () { var P = S.pub; if (!P.analysis) return; try { var id = MX.publisher.commitUpload(P.analysis); P.committed = docNo(id) || id; } catch (e) { alert(String(e)); } P.analysis = null; render(); },
    discard: function () { S.pub.analysis = null; render(); },
    verify: function (v) {
      var p = v.split(':'), id = p[0], approve = p[1] === '1';
      var item = (MX.publisher.pending() || []).filter(function (c) { return c.relation_id === id; })[0];
      try { MX.publisher.verify(id, approve); } catch (e) { alert(String(e)); return; }
      if (item) S.pub.decided[id] = { item: item, decision: approve ? 'approved' : 'rejected' };
      render();
    },
    buildver: function (v, el) { S.build.version = parseInt(el.value, 10) || S.build.version; },
    build: function () { runBuild(); },
    publish: function () { S.build.published = true; render(); },
    'run-eval': function () { runEval(); }
  };
  function analyze(name, text) {
    try { S.pub.analysis = MX.publisher.analyzeUpload(name, text); S.pub.filename = name; S.pub.committed = null; } catch (e) { alert(String(e)); }
    render();
  }

  function onClick(ev) {
    var el = ev.target.closest('[data-act]');
    if (!el || el.tagName === 'INPUT') { // click outside: close popovers
      if ((S.profileMenu || S.notifOpen) && !ev.target.closest('[data-keep]')) { S.profileMenu = S.notifOpen = false; render(); }
      return;
    }
    var act = el.getAttribute('data-act'), fn = ACT[act];
    if (fn) fn(el.getAttribute('data-arg'), el, ev);
  }
  function onKey(ev) { if (ev.key === 'Enter' && ev.target.id === 'q') { ev.preventDefault(); ask(ev.target.value); } if (ev.key === 'Escape' && (S.profileMenu || S.notifOpen)) { S.profileMenu = S.notifOpen = false; render(); } }
  function onInput(ev) { var el = ev.target.closest('[data-act]'); if (!el) return; var act = el.getAttribute('data-act'); if (act === 'draft' || act === 'buildver') ACT[act](null, el); }
  function onChange(ev) { var el = ev.target.closest('[data-act="file"]'); if (el) ACT.file(null, el); }

  /* ------------------------------------------------------------------ boot */
  function init() {
    root = document.getElementById('app');
    if (!window.MX) window.MX = makeStub();
    try { MX.init(); } catch (e) { console.error('MX.init failed', e); }
    if (!MX.state) MX.state = {};
    if (!MX.state.lang) MX.state.lang = 'ms';
    if (!MX.state.mode) MX.state.mode = 'officer';
    S = freshState();
    root.addEventListener('click', onClick);
    root.addEventListener('keydown', onKey);
    root.addEventListener('input', onInput);
    root.addEventListener('change', onChange);
    render();
  }

  /* ================================================================== STUB
     Placeholder engine, used ONLY when engine.js did not load (window.MX undefined). It implements the
     MX contract with a handful of synthetic circulars so the UI can be developed and demoed standalone.
     The real engine (engine.js) replaces all of this. */
  function makeStub() {
    var TODAY = '2026-10-07';
    function D(id, no, title, jur, cluster, issue, eff, tier, pages, langc) {
      var chunks = [], pg = pages.map(function (p, i) { return { page_no: i + 1, heading: p[0], text: p.slice(1).join('\n') }; });
      pg.forEach(function (p) { p.text.split('\n').forEach(function (ln, j) { var m = /^(\d+(?:\.\d+)*)\s+(.*)$/.exec(ln); if (m) chunks.push({ chunk_id: id + '#' + p.page_no + '.' + j, page_no: p.page_no, heading: p.heading, clause_ref: m[1], breadcrumb: no + ' > ' + p.heading + ' > ' + m[1], text: m[2] }); }); });
      return { doc_id: id, circular_no: no, title: title, issuer: 'Jabatan Perkhidmatan Contoh (Sintetik)', series: no.split(' ')[0], doc_type: 'circular', jurisdiction: jur, cluster: cluster, issue_date: issue, effective_date: eff, expiry_date: '', one_off: false, classification_level: tier, language: langc || 'ms', applicability: '', status: 'UNKNOWN', status_reason: '', pages: pg, chunks: chunks };
    }
    var docs = [
      D('SPP-3-2019', 'SPP 3/2019', 'Tuntutan Elaun Perjalanan Dalam Negeri', 'FEDERAL', 'travel-claims', '2019-05-15', '2019-06-01', 0, [['TUJUAN', '1 Surat Pekeliling ini menetapkan peraturan tuntutan elaun perjalanan dalam negeri.'], ['PERATURAN TUNTUTAN', '4.1 Tuntutan elaun perjalanan hendaklah dikemukakan dalam tempoh 30 hari dari tarikh perjalanan selesai.', '4.2 Kadar elaun perbatuan bagi pegawai yang menggunakan kenderaan sendiri ialah RM0.55 sekilometer.', '4.3 Tuntutan dikemukakan menggunakan borang kertas JPC-TP1.']]),
      D('SPP-1-2023', 'SPP 1/2023', 'Tuntutan Elaun Perjalanan Dalam Negeri dan Pelaksanaan Sistem e-Tuntutan', 'FEDERAL', 'travel-claims', '2023-02-15', '2023-03-01', 0, [['TUJUAN', '1 Surat Pekeliling ini menetapkan peraturan baharu tuntutan elaun perjalanan dan mewajibkan sistem e-Tuntutan.'], ['PERATURAN TUNTUTAN', '4.1 Tuntutan elaun perjalanan hendaklah dikemukakan dalam tempoh 60 hari dari tarikh perjalanan selesai.', '4.2 Kadar elaun perbatuan bagi pegawai yang menggunakan kenderaan sendiri untuk tugas rasmi ialah RM0.70 sekilometer.', '4.3 Semua tuntutan hendaklah dikemukakan melalui sistem e-Tuntutan. Borang kertas tidak lagi diterima.'], ['PEMBATALAN', '6 Dengan berkuat kuasanya Surat Pekeliling Perkhidmatan ini, Surat Pekeliling Perkhidmatan Bilangan 3 Tahun 2019 adalah dibatalkan.']]),
      D('SPP-2-2025', 'SPP 2/2025', 'Pindaan Kadar Elaun Perbatuan bagi Tuntutan Perjalanan Dalam Negeri', 'FEDERAL', 'travel-claims', '2025-06-10', '2025-07-01', 0, [['PINDAAN', '4 Perenggan 4.2 Surat Pekeliling Perkhidmatan Bilangan 1 Tahun 2023 dipinda seperti berikut: kadar elaun perbatuan bagi pegawai yang menggunakan kenderaan sendiri untuk tugas rasmi ialah RM0.80 sekilometer (mileage rate RM0.80 per km).', '4.2 Peruntukan lain dalam Surat Pekeliling Perkhidmatan Bilangan 1 Tahun 2023, termasuk tempoh tuntutan 60 hari, kekal berkuat kuasa.']]),
      D('PP-4-2024', 'PP 4/2024', 'Cuti Penjagaan Anak bagi Pegawai Perkhidmatan Awam Persekutuan', 'FEDERAL', 'leave', '2024-06-03', '2024-07-01', 0, [['KELAYAKAN', '4.1 Pegawai layak mendapat cuti penjagaan anak sebanyak 7 hari setahun bagi anak berumur 12 tahun ke bawah.']]),
      D('PAN-2-2024', 'PAN 2/2024', 'Cuti Penjagaan Anak bagi Perkhidmatan Awam Negeri Sarawak', 'SARAWAK', 'leave', '2024-08-12', '2024-09-01', 0, [['KELAYAKAN', '4.1 Pegawai negeri layak mendapat cuti penjagaan anak sebanyak 10 hari setahun.', '4.2 Had umur 12 tahun tidak terpakai bagi anak OKU.']]),
      D('SOP-AUDIT-2025', 'SOP 1/2025', 'Prosedur Dalaman Audit Tuntutan Perjalanan (TERHAD)', 'FEDERAL', 'travel-claims', '2025-03-05', '2025-04-01', 1, [['AMBANG AUDIT', '3.1 Tuntutan melebihi RM1,500 sebulan diaudit secara automatik.']])
    ];
    var rels = [
      { relation_id: 'R001', source_doc_id: 'SPP-1-2023', target_doc_id: 'SPP-3-2019', relation_type: 'CANCELS', scope: 'whole', effective_date: '2023-03-01', evidence_text: 'Surat Pekeliling Perkhidmatan Bilangan 3 Tahun 2019 adalah dibatalkan.', evidence_page: 3, confidence: 1, verified: true, rejected: false },
      { relation_id: 'R002', source_doc_id: 'SPP-2-2025', target_doc_id: 'SPP-1-2023', relation_type: 'AMENDS', scope: 'clauses: 4.2', effective_date: '2025-07-01', evidence_text: 'Perenggan 4.2 Surat Pekeliling Perkhidmatan Bilangan 1 Tahun 2023 dipinda seperti berikut:', evidence_page: 1, confidence: 1, verified: true, rejected: false }
    ];
    var users = [
      { user_id: 'FED-T0', name: 'Pegawai Persekutuan (Terbuka)', initials: 'PP', role: 'OFFICER', jurisdiction: 'FEDERAL', clearance_level: 0, grade: 'N29', scheme: 'Pembantu Tadbir' },
      { user_id: 'SWK-T0', name: 'Pegawai Sarawak (Terbuka)', initials: 'PS', role: 'OFFICER', jurisdiction: 'SARAWAK', clearance_level: 0, grade: 'N29', scheme: 'Pembantu Tadbir' },
      { user_id: 'FED-T1', name: 'Pegawai Terhad', initials: 'PT', role: 'OFFICER', jurisdiction: 'FEDERAL', clearance_level: 1, grade: 'N41', scheme: 'Pegawai Tadbir' }
    ];
    var GLOSS = [['perbatuan', 'mileage'], ['tuntutan', 'claim'], ['perjalanan', 'travel'], ['cuti', 'leave'], ['penjagaan anak', 'childcare'], ['kadar', 'rate'], ['tempoh', 'period'], ['hari', 'days']];
    var STOP = 'yang untuk dan di ke dari bagi saya boleh adakah berapa berapakah apakah the a an is are what how many can i for of to in my'.split(' ');
    var M = { __stub: true, data: { documents: docs, relations: rels, users: users, glossary: GLOSS, golden: [], eval: { baseline: { correct_current: 0.433, cancelled_citation_rate: 0.917, recall_at_5: 1, mrr: 0.758, citation_accuracy: 0.455, jurisdiction_accuracy: 0.6, refusal_accuracy: 0.875, false_refusal_rate: 0.091, access_leaks: 0, latency_p50_ms: 5.2, latency_p95_ms: 7.4 }, navigator: { correct_current: 0.833, cancelled_citation_rate: 0, recall_at_5: 1, mrr: 0.977, citation_accuracy: 0.818, jurisdiction_accuracy: 1, refusal_accuracy: 0.875, false_refusal_rate: 0.136, access_leaks: 0, latency_p50_ms: 7.5, latency_p95_ms: 10.9 }, by_type: [{ type: 'normal', n: 5, baseline: 3, navigator: 3 }, { type: 'trap_cancelled', n: 12, baseline: 0, navigator: 10 }, { type: 'jurisdiction', n: 5, baseline: 3, navigator: 5 }, { type: 'unanswerable', n: 5, baseline: 4, navigator: 4 }, { type: 'access', n: 3, baseline: 3, navigator: 3 }], headline_ms: 'Pada soalan perangkap, garis asas memetik pekeliling lapuk sebagai terkini dalam 91.7% kes; Navigator 0%.', headline_en: 'On trap questions the baseline presented a stale circular as current in 91.7% of cases; the Navigator in 0%.' }, today: TODAY, upload_demo: { filename: 'SPP-1-2026.md', text: '' } }, state: {} };
    function doc(id) { return docs.filter(function (d) { return d.doc_id === id; })[0]; }
    M.init = function () { M.state = { userId: 'FED-T0', lang: 'ms', mode: 'officer', includeHistorical: false, installedPacks: [{ tier: 0, version: 3, file: 'pack-terbuka-v3.json', installed_at: '2026-09-12', documents: 5, sha256: '9f2c7a0be41d3c8e41a0'.repeat(3) }, { tier: 1, version: 2, file: 'pack-terhad-v2.json', installed_at: '2026-09-12', documents: 1, sha256: '1a2b3c4d5e6f7a8b'.repeat(4) }], manifest: { version: 4, packs: [{ tier: 0, version: 4, file: 'pack-terbuka-v4.json', size_bytes: 48200, sha256: '9f2c7a0be41d'.repeat(5) + 'e41a', signature: 'd41d8cd98f00b204e9800998ecf8427e'.repeat(2), documents: 6, new_documents: 1, status_changes: 1 }] }, notifications: [{ id: 1, kind: 'UPDATE_AVAILABLE', title_ms: 'Pek Terbuka v4 sedia untuk dipasang', title_en: 'Terbuka pack v4 is ready to install', body_ms: 'Ditemui dalam saluran kemas kini pejabat.', body_en: 'Found on the office update channel.', read: false }], pendingRelations: [], queryLog: [], uploads: [] }; M.recompute(); };
    M.reset = function () { M.init(); };
    M.setUser = function (id) { M.state.userId = id; };
    M.currentUser = function () { return users.filter(function (u) { return u.user_id === M.state.userId; })[0] || users[0]; };
    M.t = function (k) { return k; };
    M.recompute = function () {
      docs.forEach(function (d) {
        var inc = rels.filter(function (r) { return r.target_doc_id === d.doc_id && r.verified && !r.rejected; });
        var kill = inc.filter(function (r) { return (r.relation_type === 'CANCELS' || r.relation_type === 'SUPERSEDES') && (!r.effective_date || r.effective_date <= TODAY); })[0];
        if (kill) { d.status = 'CANCELLED'; d.status_reason = 'Dibatalkan oleh ' + doc(kill.source_doc_id).circular_no; return; }
        var am = inc.filter(function (r) { return r.relation_type === 'AMENDS'; });
        if (am.length) { d.status = 'AMENDED'; d.status_reason = 'Dipinda oleh ' + am.map(function (r) { return doc(r.source_doc_id).circular_no; }).join(', '); return; }
        if (d.effective_date <= TODAY) { d.status = 'IN_FORCE'; d.status_reason = ''; } else { d.status = 'UNKNOWN'; d.status_reason = 'Status belum disahkan'; }
      });
    };
    M.canSee = function (d) { return (d.classification_level | 0) <= (M.currentUser().clearance_level | 0); };
    function tok(s) { var w = String(s).toLowerCase().replace(/[^a-z0-9À-ɏ.,]+/g, ' ').split(/\s+/).filter(function (x) { return x && STOP.indexOf(x) < 0; }); var out = w.slice(); w.forEach(function (x) { GLOSS.forEach(function (g) { if (g[0] === x) out.push(g[1]); if (g[1] === x) out.push(g[0]); }); }); return out; }
    M.ask = function (q, opt) {
      var t0 = performance.now(), base = opt && opt.baseline, qt = tok(q), u = M.currentUser();
      var en = /\b(what|how|can|days|rate|leave|claim)\b/i.test(q) && !/\b(berapa|boleh|saya|kadar)\b/i.test(q);
      var hits = [];
      docs.forEach(function (d) { if (!M.canSee(d)) return; d.chunks.forEach(function (c) { var ct = tok(c.text + ' ' + d.title + ' ' + c.heading); var sc = 0; qt.forEach(function (w) { if (ct.indexOf(w) >= 0) sc++; }); if (sc) hits.push({ d: d, c: c, score: sc + (d.status === 'AMENDED' && c.clause_ref === '4.2' ? -2 : 0) + (u.jurisdiction === d.jurisdiction ? 0.5 : 0) }); }); });
      hits.sort(function (a, b) { return b.score - a.score; });
      var excluded = base ? [] : hits.filter(function (h) { return h.d.status === 'CANCELLED'; }).map(function (h) { return h.d; }).filter(function (d, i, a) { return a.indexOf(d) === i; }).map(function (d) { return { doc_id: d.doc_id, circular_no: d.circular_no, status_reason: d.status_reason }; });
      var pool = base ? hits : hits.filter(function (h) { return h.d.status !== 'CANCELLED' || M.state.includeHistorical; });
      var seen = {}, top = pool.filter(function (h) { if (seen[h.d.doc_id]) return false; seen[h.d.doc_id] = 1; return true; }).slice(0, 3);
      var best = top[0] ? top[0].score : 0;
      if (best < 2) return { answerable: false, language: en ? 'en' : 'ms', answer_html: en ? "Sorry, I couldn't find this in the circulars currently in force." : 'Maaf, saya tidak menemui jawapan dalam pekeliling yang berkuat kuasa.', citations: [], excluded: excluded, confidence: 'LOW', jurisdiction_conflict: false, comparison: null, timing_ms: performance.now() - t0, query_log_id: 'q' + (M.state.queryLog.push({ q: q, answerable: false, excluded: excluded }) ) };
      var cites = top.map(function (h, i) { return { id: 'S' + (i + 1), doc_id: h.d.doc_id, circular_no: h.d.circular_no, title: h.d.title, status: h.d.status, status_reason: h.d.status_reason, jurisdiction: h.d.jurisdiction, clause_ref: h.c.clause_ref, breadcrumb: h.d.circular_no + ' > ' + h.c.heading + ' > ' + h.c.clause_ref, page_no: h.c.page_no, text: h.c.text }; });
      var html = cites.map(function (c) { return esc(c.text) + ' <span class="cite" data-id="' + c.id + '">[' + c.id + ']</span>'; }).join(' ');
      var mine = cites.filter(function (c) { return c.jurisdiction === u.jurisdiction; })[0], other = cites.filter(function (c) { return c.jurisdiction !== u.jurisdiction && c.jurisdiction !== 'FEDERAL_SARAWAK'; })[0];
      var conflict = !base && !!(mine && other && mine.circular_no.split(' ')[0] !== other.circular_no.split(' ')[0] && doc(mine.doc_id).cluster === doc(other.doc_id).cluster);
      M.state.queryLog.push({ q: q, answerable: true, excluded: excluded });
      return { answerable: true, language: en ? 'en' : 'ms', answer_html: html, citations: cites, excluded: excluded, confidence: best >= 3 ? 'HIGH' : 'MEDIUM', jurisdiction_conflict: conflict, comparison: conflict ? { mine: mine, other: other } : null, timing_ms: performance.now() - t0, query_log_id: 'q' + M.state.queryLog.length };
    };
    M.library = function () { return docs.filter(M.canSee).map(function (d) { return { no: d.circular_no, title: d.title, jurisdiction: d.jurisdiction, status: d.status, status_reason: d.status_reason, date: d.effective_date, tier: d.classification_level, doc_id: d.doc_id }; }); };
    M.document = function (id) { var d = doc(id); return d && M.canSee(d) ? d : null; };
    M.lineage = function (id) {
      var ids = [id], grow = true;
      while (grow) { grow = false; rels.forEach(function (r) { if (r.verified && !r.rejected && (ids.indexOf(r.source_doc_id) >= 0 || ids.indexOf(r.target_doc_id) >= 0)) { [r.source_doc_id, r.target_doc_id].forEach(function (x) { if (ids.indexOf(x) < 0) { ids.push(x); grow = true; } }); } }); }
      var nodes = ids.map(doc).filter(Boolean).sort(function (a, b) { return a.effective_date < b.effective_date ? -1 : 1; }).map(function (d) { var h = !M.canSee(d); return { doc_id: d.doc_id, circular_no: h ? '' : d.circular_no, title: h ? '' : d.title, status: d.status, status_reason: d.status_reason, date: d.effective_date, jurisdiction: d.jurisdiction, hidden: h }; });
      return { nodes: nodes, edges: rels.filter(function (r) { return r.verified && !r.rejected && ids.indexOf(r.source_doc_id) >= 0 && ids.indexOf(r.target_doc_id) >= 0; }).map(function (r) { return { source: r.source_doc_id, target: r.target_doc_id, type: r.relation_type, evidence: r.evidence_text, page: r.evidence_page }; }) };
    };
    M.whatChanged = function (o, n) { var a = doc(o), b = doc(n); if (!a || !b) return null; var nums = function (d) { return d.chunks.map(function (c) { return (keyFigure(c.text) || ''); }).filter(Boolean); }; var A = nums(a), B = nums(b); var pairs = A.map(function (x, i) { return B[i] && B[i] !== x ? x + ' → ' + B[i] : null; }).filter(Boolean); return { changes: [], summary_ms: pairs.length ? pairs.join('; ') : 'Tiada perubahan angka dikesan.', summary_en: pairs.length ? pairs.join('; ') : 'No numeric change detected.', effective_date: b.effective_date }; };
    M.packs = {
      manifest: function () { return M.state.manifest; },
      installed: function () { return M.state.installedPacks; },
      checkUpdates: function () { return M.state.manifest.packs.filter(function (p) { return (p.tier | 0) <= (M.currentUser().clearance_level | 0) && p.version > (M.state.installedPacks.filter(function (i) { return i.tier === p.tier; })[0] || { version: 0 }).version; }); },
      build: function (v) { return new Promise(function (res) { setTimeout(function () { M.state.manifest = { version: v, packs: [0, 1].map(function (tier) { return { tier: tier, version: v, file: 'pack-' + TIERS[tier].toLowerCase() + '-v' + v + '.json', size_bytes: 40000 + tier * 3000, sha256: ('%' + v + 'f2c7a0be41d').repeat(5).replace(/%/g, '').slice(0, 64), signature: ('s' + v + 'ig').repeat(16), documents: docs.filter(function (d) { return d.classification_level <= tier; }).length }; }) }; res(M.state.manifest); }, 200); }); },
      install: function (entry, opt) {
        return new Promise(function (res) { setTimeout(function () {
          var tamper = opt && opt.tamper, prev = M.state.installedPacks.filter(function (i) { return i.tier === entry.tier; })[0];
          var steps = [['read', 'Baca manifest.json', 'Read manifest.json', 'v' + entry.version + ' available · v' + (prev ? prev.version : 0) + ' installed', true], ['copy', 'Salin ' + entry.file, 'Copy ' + entry.file, fmtBytes(entry.size_bytes), true], ['sha256', 'Sahkan checksum SHA-256', 'Verify SHA-256 checksum', tamper ? 'mismatch' : prefix(entry.sha256), !tamper], ['signature', 'Sahkan tandatangan Ed25519', 'Verify Ed25519 signature', 'publisher public key', true], ['model', 'Semak model pembenaman', 'Check embedding model', 'none = none', true], ['atomic', 'Pasang secara atomik', 'Install atomically', 'v' + (prev ? prev.version : 0) + ' kept for rollback', true], ['compare', 'Bandingkan v' + (prev ? prev.version : 0) + ' → v' + entry.version, 'Compare v' + (prev ? prev.version : 0) + ' → v' + entry.version, '2 changes', true]].map(function (s) { return { key: s[0], label_ms: s[1], label_en: s[2], detail: s[3], ok: s[4] }; });
          if (tamper) { M.state.notifications.unshift({ id: Date.now(), kind: 'INSTALL_FAILED', title_ms: 'Pek v' + entry.version + ' ditolak: checksum tidak sepadan', title_en: 'Pack v' + entry.version + ' rejected: checksum mismatch', body_ms: 'Versi sebelumnya kekal aktif.', body_en: 'The previous version stays active.', read: false }); return res({ ok: false, steps: steps.slice(0, 3), reason: 'SHA-256 mismatch: the pack was modified after it was signed. v' + (prev ? prev.version : 0) + ' stays active.' }); }
          M.state.installedPacks = M.state.installedPacks.filter(function (i) { return i.tier !== entry.tier; }).concat([{ tier: entry.tier, version: entry.version, file: entry.file, installed_at: TODAY, documents: entry.documents, sha256: entry.sha256, previous_version: prev ? prev.version : null }]);
          M.state.notifications = [{ id: Date.now(), kind: 'STATUS_CHANGED', title_ms: 'SPP 1/2023 kini Dipinda oleh SPP 2/2025', title_en: 'SPP 1/2023 is now Amended by SPP 2/2025', body_ms: 'Kadar perbatuan RM0.70 → RM0.80.', body_en: 'Mileage rate RM0.70 → RM0.80.', read: false }].concat(M.state.notifications.filter(function (n) { return n.kind !== 'UPDATE_AVAILABLE'; }));
          res({ ok: true, steps: steps, reason: '', diff: { added: ['SPP-2-2025'], status_changes: [{ doc_id: 'SPP-1-2023', from: 'IN_FORCE', to: 'AMENDED', reason: 'Dipinda oleh SPP 2/2025' }] } });
        }, 150); });
      }
    };
    var RX = /(?:(?:surat\s+)?pekeliling\s+(?:perkhidmatan|perbendaharaan|am\s+negeri)|\b(?:spp|pp|se|pan|gp|sop|pkp)\b)\s*(?:bilangan|bil\.?)?\s*(\d{1,3})\s*(?:tahun|\/)\s*((?:19|20)\d{2})/ig;
    M.publisher = {
      demoUploadText: function () { return 'SINTETIK - CONTOH SAHAJA\n\n# SURAT PEKELILING PERKHIDMATAN BILANGAN 1 TAHUN 2026\n\nTajuk: Tuntutan Elaun Perjalanan Dalam Negeri (Penyelarasan 2026)\nRujukan: SPP 1/2026\nTarikh kuat kuasa: 1 Oktober 2026\n\n## PERATURAN TUNTUTAN\n\n4.1 Tuntutan elaun perjalanan hendaklah dikemukakan melalui sistem e-Tuntutan dalam tempoh 90 hari dari tarikh perjalanan selesai.\n\n4.2 Kadar elaun perbatuan ialah RM0.85 sekilometer.\n\n## PEMBATALAN\n\n6. Dengan berkuat kuasanya Surat Pekeliling Perkhidmatan ini, Surat Pekeliling Perkhidmatan Bilangan 1 Tahun 2023 dan Surat Pekeliling Perkhidmatan Bilangan 2 Tahun 2025 adalah dibatalkan.'; },
      analyzeUpload: function (name, text) {
        var cands = [], m, secs = text.split(/\n(?=## )/), own = /BILANGAN\s+(\d+)\s+TAHUN\s+(\d{4})/i.exec(text);
        secs.forEach(function (sec, pi) { RX.lastIndex = 0; while ((m = RX.exec(sec))) { var no = m[1] + '/' + m[2]; if (own && no === own[1] + '/' + own[2]) continue; var tgt = docs.filter(function (d) { return d.circular_no.split(' ')[1] === no; })[0]; var type = /dibatalkan|membatalkan|dimansuhkan|digantikan|cancel|supersed|revoked|replaces/i.test(sec) ? 'CANCELS' : /dipinda|pindaan|meminda|amend/i.test(sec) ? 'AMENDS' : 'REFERENCES'; cands.push({ relation_id: 'U' + (cands.length + 1), target_doc_id: tgt ? tgt.doc_id : '', target_ref_text: m[0], relation_type: type, evidence_text: sec.replace(/^##\s*\S+\s*/, '').trim().slice(0, 300), evidence_page: pi + 1, confidence: tgt ? 0.9 : 0.5 }); } });
        var pages = secs.map(function (s, i) { return { page_no: i + 1, heading: (/^##\s*(.*)$/m.exec(s) || [])[1] || '', text: s.replace(/^##.*$/m, '').trim() }; });
        return { meta: { doc_id: 'SPP-1-2026', circular_no: 'SPP 1/2026', title: (/Tajuk:\s*(.*)/.exec(text) || [])[1] || name, issuer: 'Jabatan Perkhidmatan Contoh (Sintetik)', doc_type: 'circular', jurisdiction: 'FEDERAL', issue_date: '2026-09-15', effective_date: '2026-10-01', classification_level: 0 }, candidates: cands, pages: pages, text: text };
      },
      commitUpload: function (A) { var d = D(A.meta.doc_id, A.meta.circular_no, A.meta.title, A.meta.jurisdiction, 'travel-claims', A.meta.issue_date, A.meta.effective_date, 0, A.pages.map(function (p) { return [p.heading].concat(p.text.split('\n').filter(Boolean)); })); if (!doc(d.doc_id)) docs.push(d); A.candidates.forEach(function (c) { M.state.pendingRelations.push({ relation_id: c.relation_id, source_doc_id: d.doc_id, target_doc_id: c.target_doc_id, target_ref_text: c.target_ref_text, relation_type: c.relation_type, scope: 'whole', effective_date: A.meta.effective_date, evidence_text: c.evidence_text, evidence_page: c.evidence_page, confidence: c.confidence, verified: false, rejected: false }); }); M.recompute(); return d.doc_id; },
      pending: function () { return M.state.pendingRelations.filter(function (r) { return !r.verified && !r.rejected; }); },
      verify: function (id, ok) { M.state.pendingRelations.forEach(function (r) { if (r.relation_id === id) { r.verified = !!ok; r.rejected = !ok; if (ok) rels.push(r); } }); M.recompute(); if (ok) M.state.notifications.unshift({ id: Date.now(), kind: 'STATUS_CHANGED', title_ms: 'Status dikemas kini selepas pengesahan ' + id, title_en: 'Status updated after verifying ' + id, body_ms: '', body_en: '', read: false }); }
    };
    M.notifications = function () { return M.state.notifications; };
    M.markRead = function () { M.state.notifications.forEach(function (n) { n.read = true; }); };
    M.evaluation = function () { return M.data.eval; };
    M.analytics = function () { var log = M.state.queryLog, counts = {}, ex = {}; log.forEach(function (r) { counts[r.q] = (counts[r.q] || 0) + 1; (r.excluded || []).forEach(function (e) { ex[e.circular_no] = (ex[e.circular_no] || 0) + 1; }); }); return { total_queries: log.length, unanswered_rate: log.length ? log.filter(function (r) { return !r.answerable; }).length / log.length : 0, top_questions: Object.keys(counts).map(function (q) { return { question: q, count: counts[q] }; }).sort(function (a, b) { return b.count - a.count; }), top_excluded: Object.keys(ex).map(function (k) { return { circular_no: k, count: ex[k] }; }).sort(function (a, b) { return b.count - a.count; }) }; };
    return M;
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init); else init();
  return { render: render, ask: ask, state: function () { return S; }, t: t, labels: L };
})();
