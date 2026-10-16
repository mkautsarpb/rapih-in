[English](README.md) | [Bahasa Indonesia](README.id.md)

<p align="center">
  <img src="assets/branding/rapih-in-logo.png" alt="Logo rapih-in: monogram r geometris berwarna teal yang tersusun dari blok kode dengan kotak mint, di samping wordmark rapih-in" width="420">
</p>

<p align="center">
  <strong>Rapikan struktur proyek yang sudah berjalan, lalu jaga file baru tetap berada di tempat yang tepat.</strong><br>
  <em>Struktur rapi. Refactor yang terarah.</em>
</p>

<p align="center">
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-038982" alt="Lisensi: MIT"></a>
</p>

rapih-in adalah Agent Skill untuk coding agent (Codex, Claude Code, Google Antigravity, Cursor Agent, Kimi Code CLI). Skill ini mengaudit struktur folder dan tanggung jawab tiap file, mengusulkan perubahan terkecil yang benar-benar berguna, menerapkannya per batch dengan checkpoint tanpa mengubah perilaku aplikasi, lalu membantu agent menaruh file baru di tempat yang semestinya.

## Daftar isi

- [Mengapa rapih-in](#mengapa-rapih-in)
- [Mulai cepat untuk proyek lama](#mulai-cepat-untuk-proyek-lama)
- [Instalasi](#instalasi)
- [Host dan cara memanggil](#host-dan-cara-memanggil)
- [Mode](#mode)
- [Opsi](#opsi)
- [Cara kerja sebuah run](#cara-kerja-sebuah-run)
- [Memecah file berdasarkan tanggung jawab](#memecah-file-berdasarkan-tanggung-jawab)
- [Pemakaian sehari-hari](#pemakaian-sehari-hari)
- [Pemecahan masalah](#pemecahan-masalah)
- [Status validasi dan batasan](#status-validasi-dan-batasan)
- [Kontribusi](#kontribusi)
- [Dukungan](#dukungan)
- [Star History](#star-history)
- [Lisensi](#lisensi)

## Mengapa rapih-in

Skill untuk organisasi file dan arsitektur sudah ada sebelumnya. rapih-in berfokus pada mutu setiap keputusan dan pada migrasi yang bisa Anda periksa:

| Tujuan | Yang dilakukan skill |
| --- | --- |
| Mengikuti karakter repo | Membaca konfigurasi framework, manifest, dan kode di sekitarnya; setiap keputusan lokasi menyebut file atau konfigurasi pendukungnya. Package yang berbeda boleh mempertahankan struktur masing-masing yang valid. |
| Perubahan minimum yang berguna | Mengusulkan pemindahan atau pemecahan hanya bila manfaatnya konkret; hal kosmetik ditandai opsional dan tidak diterapkan secara default; repo yang sudah rapi tidak diubah. |
| Dampak migrasi yang terlihat | Preview menampilkan file yang dipindah, simbol yang diekstrak, edit pada file asal, file baru, import yang diperbarui, serta pemeriksaan yang akan dijalankan. |
| Pemecahan sesuai tanggung jawab | Mengekstrak fungsi, komponen, hook, class, atau module yang punya pemilik jelas; file panjang yang kohesif dibiarkan utuh. |
| Bisa dilanjutkan dan dipulihkan | Satu lock penulis per worktree, checkpoint per batch, deteksi edit yang Anda lakukan di tengah jalan, dan pemulihan terarah untuk satu batch. |
| Hasil yang dapat diperiksa | Sebelum/sesudah pada cakupan dan metode yang sama, dengan pemeriksaan lulus, gagal sejak awal, regresi baru, dan belum dijalankan dipisahkan. Tanpa skor kesehatan. |
| Konsisten setelahnya | Tugas coding berikutnya memakai ownership hasil perapian tanpa mengaudit ulang seluruh repo. |

Ini adalah target desain. Apa yang benar-benar sudah diuji tercantum di [Status validasi dan batasan](#status-validasi-dan-batasan).

## Mulai cepat untuk proyek lama

1. Pasang skill untuk agent Anda (lihat [Instalasi](#instalasi)). Pemasangan tidak pernah memulai perapian dengan sendirinya.
2. Di chat agent, buka proyek lalu jalankan audit (hanya membaca):

   ```text
   /rapih-in audit
   ```

3. Tinjau preview lengkap. Tidak ada yang diubah dan tidak ada checkpoint yang ditulis:

   ```text
   /rapih-in all --dry-run
   ```

4. Terapkan semua yang layak, atau hanya temuan yang Anda pilih:

   ```text
   /rapih-in all
   /rapih-in fix --only R001,R003
   ```

Perintah di atas memakai prefix Claude Code dan Cursor. Codex memakai `$rapih-in`, Kimi memakai `/skill:rapih-in`; lihat [Host dan cara memanggil](#host-dan-cara-memanggil). Bila mau, `/rapih-in all` langsung menjalankan seluruh urutan audit, plan, fix, dan check sekaligus.

## Instalasi

### Prasyarat

- Satu atau lebih agent yang didukung sudah terpasang.
- Python 3.8 atau lebih baru untuk helper state (`python`, `python3`, atau `py -3`). Helper hanya memakai standard library. Tanpa Python, rapih-in tetap bisa mengaudit dan menyusun rencana, tetapi tidak menerapkan perubahan.
- Git bersifat opsional; dengan Git, baseline ikut mencatat perubahan Anda yang belum di-commit.

### Ambil source

```bash
git clone https://github.com/mkautsarpb/rapih-in.git
cd rapih-in
```

Skill-nya sendiri berada di `skills/rapih-in/`.

### Scope user (semua proyek di komputer ini)

Jalankan di terminal dari root repository:

```bash
python tools/sync.py plan      # show what would be installed, change nothing
python tools/sync.py install   # install for the agents detected on this machine
python tools/sync.py verify    # confirm every installed copy matches the source
```

`install` mendeteksi Codex, Claude Code, Antigravity (App/IDE dan CLI), Cursor, dan Kimi, lalu hanya menulis yang dibutuhkan masing-masing:

| Lokasi | Dibaca oleh |
| --- | --- |
| `~/.agents/skills/rapih-in/` | Codex, Cursor, Kimi Code |
| `~/.claude/skills/rapih-in/` | Claude Code (Cursor juga membacanya) |
| `~/.gemini/config/skills/rapih-in/` | Antigravity App dan IDE |
| `~/.gemini/antigravity-cli/skills/rapih-in/` | Antigravity CLI |

Di samping setiap folder `rapih-in/` juga ditaruh tujuh folder pintasan (`rapih-in-audit`, `rapih-in-all`, ...); lihat [Perintah pintasan](#perintah-pintasan).

Instalasi juga menambahkan pengingat singkat agar agent ingat memakai skill ini: blok bertanda di `~/.codex/AGENTS.md`, file `~/.claude/rules/rapih-in.md`, file `~/.gemini/config/rules/rapih-in.md` (`trigger: always_on`), dan blok di `~/.kimi-code/AGENTS.md` bila Kimi terpasang. User Rules di Cursor adalah pengaturan UI: jalankan `python tools/sync.py reminder` lalu tempel teksnya di Cursor Settings, Rules, User Rules. Instruksi yang sudah ada tetap dipertahankan; pemasangan ulang tidak menggandakan pengingat.

Pilih host secara eksplisit dengan `--hosts codex,claude`. Instalasi scope user tidak terlihat oleh cloud agent, remote SSH, container, atau WSL; pasang terpisah di lingkungan tersebut.

### Scope project (satu repository)

```bash
python tools/sync.py install --scope project --project /path/to/your/repo
```

Perintah ini menulis `.agents/skills/rapih-in/` (dibaca Codex, Cursor, Kimi, Antigravity), `.claude/skills/rapih-in/` bila Claude Code menjadi target, dan blok pengingat di `AGENTS.md` repo tersebut. Gunakan scope user atau project untuk satu host, jangan keduanya, agar dua salinan bernama sama tidak saling bersaing.

### Pembaruan

Ubah atau tarik source terbaru, lalu jalankan lagi `python tools/sync.py install` dan `python tools/sync.py verify`. Setiap salinan diganti dari satu source di `skills/rapih-in/`; `verify` gagal bila ada salinan yang berbeda isi. Salinan yang Anda ubah manual dilaporkan, bukan ditimpa.

### Menghapus instalasi

```bash
python tools/sync.py uninstall
```

Hanya menghapus salinan dan pengingat yang dibuat oleh `tools/sync.py` (bertanda `.rapih-in-install.json`, marker rapih-in, atau header rapih-in). Skill lain dan instruksi Anda sendiri tidak disentuh. State run di `~/.rapih-in/` tetap disimpan; hapus sendiri bila checkpoint lama tidak diperlukan lagi.

## Host dan cara memanggil

Semua contoh diketik di chat agent, bukan di terminal.

| Host | Pemanggilan eksplisit | Pemakaian otomatis | Diuji di sini |
| --- | --- | --- | --- |
| Codex CLI / IDE | `$rapih-in all --dry-run` | Ya | CLI 0.162.0: discovery dan `audit` diuji |
| Claude Code | `/rapih-in all --dry-run` | Ya | 2.1.301: semua mode kecuali `plan`/`check` diuji, plus pemakaian implisit |
| Cursor Agent | `/rapih-in all --dry-run` | Ya | Belum diuji (tidak terpasang) |
| Kimi Code CLI | `/skill:rapih-in all --dry-run` | Ya | Belum diuji (tidak terpasang) |
| Antigravity App / CLI | `/rapih-in all --dry-run` | Ya | Belum diuji |
| Antigravity IDE | "Gunakan skill rapih-in mode all dengan --dry-run pada proyek ini." | Ya | Terpasang, belum diuji |

Rincian per host, termasuk folder discovery dan catatan versi: [skills/rapih-in/references/host-compatibility.md](skills/rapih-in/references/host-compatibility.md).

### Perintah pintasan

Instalasi juga menambahkan satu perintah untuk setiap mode, sehingga Anda cukup memilihnya dari menu `/` tanpa mengetik nama mode:

| Mode | Claude Code, Cursor, Antigravity App/CLI | Codex | Kimi Code |
| --- | --- | --- | --- |
| `audit` | `/rapih-in-audit` | `$rapih-in-audit` | `/skill:rapih-in-audit` |
| `plan` | `/rapih-in-plan` | `$rapih-in-plan` | `/skill:rapih-in-plan` |
| `fix` | `/rapih-in-fix` | `$rapih-in-fix` | `/skill:rapih-in-fix` |
| `check` | `/rapih-in-check` | `$rapih-in-check` | `/skill:rapih-in-check` |
| `place` | `/rapih-in-place` | `$rapih-in-place` | `/skill:rapih-in-place` |
| `all` | `/rapih-in-all` | `$rapih-in-all` | `/skill:rapih-in-all` |
| `resume` | `/rapih-in-resume` | `$rapih-in-resume` | `/skill:rapih-in-resume` |

Setiap pintasan hanyalah pintu masuk tipis: ia memuat skill utama `rapih-in` lalu menjalankan mode tersebut dengan argumen yang Anda ketik sesudahnya, sehingga `/rapih-in-audit src/` berperilaku persis seperti `/rapih-in audit src/`. Pintasan hanya berjalan bila dipanggil manual dan tidak pernah dipilih otomatis; bantuan otomatis saat coding tetap datang dari `rapih-in`. Untuk memasang tanpa pintasan: `python tools/sync.py install --no-shortcuts`.

## Mode

| Mode | Fungsinya | Mengubah source |
| --- | --- | --- |
| `help` | Tujuan, mode, opsi, contoh | Tidak |
| `audit [path]` | Temuan dengan `audit_id` dan ID (R001, R002, ...), bukti, dampak, prioritas | Tidak |
| `plan [path]` | Struktur tujuan, peta file dan simbol, kontrak yang dipertahankan, batch, pemeriksaan | Tidak |
| `fix [path]` | Menerapkan rencana yang masih valid (audit dan plan dulu bila perlu), lalu memvalidasi | Ya |
| `check [path]` | Memeriksa import, referensi, dan perilaku terdampak tanpa auto-fix | Tidak |
| `place <need>` | Merekomendasikan lokasi file, fitur, atau bagian yang akan diekstrak, beserta alasannya | Tidak |
| `all [path]` | Audit baru, lalu plan, fix, dan check, dengan checkpoint per batch | Ya |
| `resume` | Melanjutkan run yang belum selesai dengan pilihan dan batas aslinya | Mengikuti run |

Memanggil skill tanpa mode dan tanpa tugas menampilkan help singkat. Saat agent memuat skill sendiri di tengah tugas biasa, skill hanya membantu penempatan yang dibutuhkan tugas itu.

## Opsi

| Opsi | Mode | Arti |
| --- | --- | --- |
| `[path]` | audit, plan, fix, check, all | Membatasi target pada satu file atau folder. Pembaruan import pendukung di luarnya ditampilkan dalam rencana. |
| `--dry-run` | fix, all, resume | Hanya preview: peta dan ringkasan diff, tanpa perubahan file, tanpa lock, tanpa checkpoint. |
| `--exclude <path-or-glob>` | audit, plan, fix, check, all | Jangan pernah memindahkan, mengedit, menghapus, atau membuat apa pun di sana. Bisa diulang. |
| `--only <ID,...>` | plan, fix, check, all | Hanya temuan ini dari audit atau run yang dirujuk. |

Contoh:

```text
/rapih-in audit src/features/checkout/CheckoutPage.tsx
/rapih-in plan --only R001,R003
/rapih-in fix --only R001,R003 --dry-run
/rapih-in all src/ --exclude src/generated/ --exclude "src/legacy/**"
/rapih-in place fitur notifikasi
/rapih-in resume
```

## Cara kerja sebuah run

### ID temuan dan `--only`

Setiap audit punya `audit_id`; setiap temuan mendapat ID seperti `R001` yang hanya bermakna bersama audit tersebut. Temuan juga membawa fingerprint dari jenis, path, dan simbolnya, sehingga `all --only R001` bisa mengaudit ulang dan tetap mencocokkan masalah yang sama. Bila ID tidak dikenal, kedaluwarsa, atau ambigu, rapih-in menyampaikannya dan tidak mengubah hal lain sebagai gantinya. Bila memperbaiki R001 membutuhkan perubahan substantif pada temuan yang tidak dipilih, R001 ditandai blocked beserta dependensinya.

### Checkpoint, resume, dan pemulihan

Run yang mengubah file (`fix`, `all`, `resume`) menyimpan state di luar repo Anda, di `~/.rapih-in/runs/<repo-key>/<run-id>/`: scope, exclusion, ID terpilih, rencana, dan snapshot hanya untuk file yang disentuh tiap batch (tidak pernah file `.env` atau key). Bila run berhenti di tengah, `resume` mendiagnosis tiap batch, memisahkan tulisan milik run dari edit yang Anda buat, lalu melanjutkan tanpa mengulang pekerjaan yang sudah selesai. Untuk membatalkan satu batch, minta dengan kalimat biasa, misalnya "pulihkan rapih-in run R-20261016T091500-a1b2 batch b2". Hanya file yang masih sama dengan hasil tulisan run yang dipulihkan; file yang Anda ubah sesudahnya dilaporkan sebagai konflik dan dibiarkan. rapih-in tidak pernah memakai `git reset --hard` atau `git clean`.

### Lock dan status busy

Hanya satu run rapih-in yang menulis ke sebuah worktree pada satu waktu. Lock disimpan di `~/.rapih-in/locks/<repo-key>/` dan diambil secara atomik. Run kedua melaporkan `busy` beserta run pemiliknya dan tidak mengubah apa pun. Lock tidak pernah kedaluwarsa karena umur: mengambil alih lock milik run yang crash mensyaratkan pemiliknya dipastikan sudah tidak aktif. Lock hanya mengoordinasikan run rapih-in pada mesin dan user yang sama; perubahan dari editor atau tool lain dideteksi melalui hash isi file tepat sebelum setiap penulisan.

## Memecah file berdasarkan tanggung jawab

Jumlah baris hanya sinyal. File dipecah bila mencampur tanggung jawab yang berubah karena alasan berbeda. Ilustrasi (bukan hasil fixture): `CheckoutPage` yang merender form, menyimpan state form, memvalidasi input, dan memanggil API order dapat menjadi:

| Bagian | Tujuan | Alasan |
| --- | --- | --- |
| Komposisi halaman | tetap di `CheckoutPage` | menghubungkan bagian-bagian halaman |
| Aturan validasi | `features/checkout/validation/` | bisa diuji sendiri |
| Pemanggilan API order | `features/checkout/api/` | detail transport |
| State form dan alur submit | `features/checkout/hooks/` | alasan perubahan yang berbeda |

Semuanya tetap di dalam fitur checkout. Tabel mata uang 300 baris dengan dua accessor tetap satu file, dan kode generated tidak pernah dipecah. Hasil nyata pada fixture uji ada di [docs/evaluation.md](docs/evaluation.md).

## Pemakaian sehari-hari

Setelah perapian, permintaan biasa sudah cukup; agent memuat skill ketika tugas membuat, memindahkan, atau memecah file:

```text
Tambahkan input kupon di halaman checkout, lengkap dengan test.
Gunakan rapih-in untuk mengaudit repository ini.
Pindahkan helper di src/utils ke fitur yang memakainya; tanpa perubahan kode lain.
Pecah CheckoutPage berdasarkan tanggung jawab dan pertahankan perilaku serta tampilannya.
```

Permintaan yang hanya memindahkan folder tetap terbatas pada pemindahan. Bug fix kecil tidak memicu audit atau pemecahan file.

## Pemecahan masalah

| Masalah | Yang perlu dilakukan |
| --- | --- |
| Agent tidak mengenal skill | Jalankan `python tools/sync.py verify`. Di Claude Code jalankan `/reload-skills` bila `~/.claude/skills` baru dibuat selama sesi; mulai ulang sesi Codex atau Antigravity. |
| `/rapih-in` tidak berpengaruh di Codex atau Kimi | Gunakan syntax host: `$rapih-in ...` di Codex, `/skill:rapih-in ...` di Kimi, atau sebut nama skill dengan kalimat biasa di Antigravity IDE. |
| "Audit ID not found" atau "stale" | ID terikat pada satu audit. Jalankan `audit` lagi di sesi yang sama, lalu pakai ID yang baru. |
| "busy" | Run rapih-in lain sedang memegang lock worktree. Biarkan selesai, atau `resume` bila itu run Anda yang terputus. |
| Pemeriksaan berstatus "not run" | Repo tidak mendefinisikan perintah yang bisa dijalankan untuk pemeriksaan itu, atau butuh layanan yang tidak tersedia. rapih-in melaporkannya alih-alih mengklaim berhasil. |
| Python tidak ditemukan | Pasang Python 3.8+ atau sediakan `python3`/`py -3`; sampai saat itu rapih-in hanya mengaudit dan menyusun rencana. |

## Status validasi dan batasan

Hasil terukur, lingkungan, dan status setiap skenario ada di [docs/evaluation.md](docs/evaluation.md). Ringkasan:

- Sudah diimplementasikan: delapan mode dan empat opsi sebagai instruksi di `SKILL.md` beserta referensinya; helper state untuk lock, checkpoint, snapshot, diagnosis, dan pemulihan; tool install/verify/uninstall; validator paket statis.
- Diuji otomatis: 30 test script (lock dengan 8 proses serentak, penolakan lock lama, guard, interupsi, pemulihan, tool instalasi) dan validasi paket statis, semuanya lulus di Windows 11.
- Diuji melalui agent sungguhan: 30 kasus tercatat pada fixture kecil (28 dengan Claude Code 2.1.301, 2 dengan Codex CLI 0.162.0, termasuk perintah pintasan), masing-masing satu kali. Satu kasus gagal (agent mengambil alih lock run yang crash tanpa bertanya); kontrak dan helper sudah diperbaiki dan uji ulangnya lulus. Dari 37 skenario rencana, 23 terbukti, 13 sebagian, 1 belum diuji.
- Belum diuji: `plan` dan `check` sebagai mode tersendiri, fixture dengan baseline yang sudah gagal, Cursor Agent dan Kimi Code CLI (tidak terpasang di sini), perilaku di Antigravity (hanya file yang dipasang), filesystem POSIX, lingkungan remote. Tidak ada perbandingan dengan skill lain yang dijalankan, sehingga tidak ada klaim lebih unggul, dan kasus yang lulus tidak menjamin bebas regresi di proyek lain.

## Kontribusi

Issue dan pull request dipersilakan setelah repository publik diterbitkan. Jaga `SKILL.md` tetap ringkas, taruh rincian di `skills/rapih-in/references/`, dan jaga kedua README tetap setara. Sebelum mengirim:

```bash
python -m unittest discover -s tests
python tools/validate.py
```

## Dukungan

Laporkan bug dan ajukan pertanyaan di [issue tracker](https://github.com/mkautsarpb/rapih-in/issues).

## Star History

<a href="https://www.star-history.com/?repos=mkautsarpb%2Frapih-in&type=date&legend=top-left">
 <picture>
   <source media="(prefers-color-scheme: dark)" srcset="https://api.star-history.com/chart?repos=mkautsarpb/rapih-in&type=date&theme=dark&legend=top-left" />
   <source media="(prefers-color-scheme: light)" srcset="https://api.star-history.com/chart?repos=mkautsarpb/rapih-in&type=date&legend=top-left" />
   <img alt="Star History chart for mkautsarpb/rapih-in" src="https://api.star-history.com/chart?repos=mkautsarpb/rapih-in&type=date&legend=top-left" />
 </picture>
</a>

## Lisensi

[MIT](LICENSE) © 2026 rapih-in contributors.
