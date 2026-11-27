# Test files

Sample files for upload, scanning and preview tests. None holds real data.

## Committed samples

One small, valid file per allowed format ([decisions.md](../../docs/decisions.md) file formats), made with LibreOffice and FFmpeg in the worker image:

| File | Format | Notes |
| --- | --- | --- |
| `sample.pdf` | PDF | One page of text |
| `sample.doc`, `sample.docx` | Word | The same text |
| `sample.xls`, `sample.xlsx`, `sample.csv` | Spreadsheet | Three rows |
| `sample.ppt`, `sample.pptx` | PowerPoint | One slide |
| `sample.jpg`, `sample.png` | Image | 320×240, plain blue |
| `sample.mp4` | Video | 2 seconds, 640×360, H.264 |
| `sample.mp3` | Audio | 2 seconds of a 440 Hz tone |
| `pdf-renamed.docx` | PDF with a `.docx` name | Must be refused as a type mismatch (`P2-UPL-03`) |

## Generated on demand

These go into `generated/`, which git ignores:

```bash
uv run python scripts/make_test_files.py
```

| File | Size | Use |
| --- | --- | --- |
| `generated/image-21mb.jpg` | 21 MB | A real JPEG over the 20 MB image limit (D-01). Upload must refuse it |
| `generated/eicar.txt` | 68 bytes | The standard EICAR antivirus test file. It is harmless, but ClamAV reports it as `Eicar-Test-Signature`, so it must be quarantined (`P2-UPL-03`) |
| `generated/video-1gb.mp4` | 1,000 MB | A real MP4 padded to near the 1 GB media limit, for the resumable upload test (AC-11) |

Add `--skip-video` to leave out the 1 GB file. They are not committed because two are too big for git, and antivirus tools on laptops would quarantine a committed EICAR file in every checkout.
