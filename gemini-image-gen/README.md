# gemini-image-gen

A tiny, single-file tool for generating and editing images with the Gemini API
image models. Import it as a library or run it from the command line. No SDK, one
dependency (`requests`).

## Install

```bash
pip install -r requirements.txt
```

`Pillow` is optional and only used to print output dimensions after a CLI run.

## API key

Get a key at https://aistudio.google.com/apikey, then provide it any of these ways
(checked in order):

1. `GEMINI_API_KEY` environment variable
2. `GEMINI_API_KEY_FILE` pointing at a one-line file
3. `gemini_api_key.txt` sitting next to `gemini_gen.py`
4. `gemini_api_key.txt` in the current directory
5. `secrets/gemini_api_key.txt` in the current directory

Copy `gemini_api_key.txt.example` to `gemini_api_key.txt` and paste your key in,
or set the env var. **Do not commit the real key** — `.gitignore` already excludes it.

## Command line

```bash
# text to image
python gemini_gen.py "a red bicycle leaning on a white wall" -o out.png

# bigger, and a different aspect ratio
python gemini_gen.py "a mountain range at dawn" -o wide.png --size 4K --aspect 16:9

# edit or composite: input images come first, prompt is the instruction
python gemini_gen.py "make the sky deep purple" -o edited.png -i original.png
python gemini_gen.py "place this logo on a ceramic mug" -o mug.png -i logo.png
```

Options: `--size 1K|2K|4K` (default 2K), `--aspect` (default 1:1),
`--model` (default `gemini-3.1-flash-image`), `-i/--image` (repeatable).

## As a library

```python
from gemini_gen import generate

generate("a red bicycle on a white background", "out.png")
generate("a mountain range at dawn", "wide.png", size="4K", aspect="16:9")
generate("put this logo on a coffee mug", "mug.png", images=["logo.png"])
```

`generate()` returns the output path. It creates parent directories, and retries
with backoff on rate limits and transient 5xx errors (5 attempts). On a hard
error it exits with a message; wrap the call if you need to catch that instead.

## Notes

- The default model id is `gemini-3.1-flash-image`. Override with `--model` or the
  `model=` argument if you want a different image model.
- Image models do not output transparency. If you need a transparent background,
  generate on a flat key colour (e.g. bright magenta) and chroma-key it afterward.
