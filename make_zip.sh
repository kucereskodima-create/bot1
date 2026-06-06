#!/bin/bash
zip -r bot_clean.zip . \
  --exclude "*.pyc" \
  --exclude "__pycache__/*" \
  --exclude ".git/*" \
  --exclude ".cache/*" \
  --exclude ".local/*" \
  --exclude ".pythonlibs/*" \
  --exclude "attached_assets/*" \
  --exclude "assets/*" \
  --exclude ".agents/*" \
  --exclude "bot_clean.zip" \
  --exclude "make_zip.sh"
echo "Готово! Размер:"
du -sh bot_clean.zip
