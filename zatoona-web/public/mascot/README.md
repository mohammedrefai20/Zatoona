# Mascot mood art (optional)

The olive animates a single image into 6 moods via motion. For richer character, generate the **mood variants** from prompt #2 in `../../logo-prompts.md` and drop them here with these exact names (transparent PNG, same framing/proportions as the hero mascot):

```
idle.png    relaxed neutral smile
think.png   head tilted, hand on chin (used during uploads & generation)
cheer.png   arms up, celebrating (great score)
wave.png    friendly wave (login, mid score)
sad.png     gentle encouraging look (low score) — NOT distressed
peek.png    peeking from the lower edge (empty states)
```

Then enable them: set `USE_MOOD_ART = true` in `src/components/Mascot.tsx`. Any mood whose file is missing falls back to the default mascot automatically.
