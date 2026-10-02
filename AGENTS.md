# SOFTURE SKILLS: agent rules

## Language: English only in code

Everything that lands in the repository is written in **English**: code, identifiers, comments,
commit messages, script output, log and error messages, file and folder names, configuration keys,
and skill or agent instructions. This holds even when the conversation with the owner is in Polish.

- Do not translate the conversation into the code. A Polish request still produces English code.
- User-facing product copy is the only exception. It lives in message dictionaries (e.g. `messages/pl.ts`),
  never inline in code.
- When you touch a file that contains Polish code, comments or identifiers, translate them in the
  same change.
- Before every commit, check the diff for Polish (Polish diacritics and Polish words) outside
  message dictionaries. Treat any hit as a failing gate.
