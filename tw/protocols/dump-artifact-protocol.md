# Dump Artifact Protocol — 页面证据落盘唯一真相源

## 1. 位置（唯一）
`.claude/workflows/<feature>/page_cache/` 或 `.claude/record-workflows/<feature>/page_cache/`。
禁止把证据写到当前工作目录或使用自由文件名。

## 2. 目录结构
```
page_cache/
├── manifest.json
└── <slug>/
    ├── dom.html | ui.xml
    ├── screenshot.png
    ├── a11y_tree.txt        # 可选，仅 Web
    └── <state>/             # 可选，多状态页
```

## 3. manifest.json（§5.10）
`version` / `feature` / `workflow` / `created_at` / `updated_at` / `source` / `capture_mode` / `env` / `pages[]`。
每个 page：`name` / `slug` / `step` / `action` / `captured_at` / `files{dom,screenshot,a11y_tree}` / `states` / `user_note`。

## 4. slug
kebab-case，由页面名 + 操作序号生成，稳定可复现。多状态页在 slug 下再分 `<state>/` 子目录。

## 5. 消费顺序（硬约束）
`screenshot.png` → `a11y_tree.txt` → 结构树（`dom.html` / `ui.xml`，仅兜底）。不得跳级。

## 6. gitignore
`page_cache/` 不进 git；`storage_state.json` 含 auth token 绝不进 git；`.current` 不进 git。
