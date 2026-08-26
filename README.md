# ClassWidgets 集控仓库

本仓库通过 GitHub Pages 向 ClassWidgets 下发课程表和一次性公告。课程表必须放在仓库根目录独立的 **`课程表/`** 文件夹中；不要再创建或使用 `schedules/` 文件夹。

```text
.
├── manifest.json
├── 课程表/
│   ├── class-a.json
│   └── class-b.json
└── .github/
    ├── scripts/
    │   ├── publish_announcement.py
    │   └── select_schedule.py
    └── workflows/
        ├── publish-announcement.yml
        └── select-schedule.yml
```

## 添加课程表

将从 ClassWidgets 导出的课程表 JSON 直接放入 `课程表/`。文件名应使用稳定且可读的名称，例如 `class-a.json` 或 `grade1-class3.json`。课程表文件必须是 UTF-8 JSON，并包含有效的 `meta` 对象。

不要手动计算 SHA-256 或手动维护 `manifest.json` 的 `schedules` 数组。运行“选择集控课程表”工作流后，脚本会重新计算所有课程表哈希并更新清单。

## 选择要自动切换的课程表

在 GitHub 仓库页面打开 **Actions → 选择集控课程表 → Run workflow**。在输入框中填写你要选择的、位于 `课程表/` 顶层的 JSON 文件名，例如：

```text
class-a.json
```

工作流只接受文件名，不接受路径、`../`、绝对路径或非 JSON 文件。它会执行以下确定性操作：

| 操作 | 结果 |
|---|---|
| 所选文件 | 在课程表 JSON 根对象写入 `"yes": {"id": 1}`。 |
| 同一 `课程表/` 文件夹中的其余 JSON | 写入 `"yes": {"id": 0}`。 |
| `manifest.json` | 重建 `schedules` 数组，更新每份文件的 SHA-256、相对地址与策略版本。 |
| Git 提交 | 仅在内容有变化时，以 `github-actions[bot]` 创建一次可审计提交。 |

ClassWidgets 客户端仅当下发的所有课表中**恰好一份** `yes.id` 为 `1` 时才会自动切换到它。全部为 `0` 时只同步保存；若两份及以上为 `1`，客户端会拒绝自动切换。工作流会确保在正常运行后始终只有所选的一份为 `1`。

> 选择由管理员手动完成。工作流不会根据文件名、课程表名称或设备信息猜测要选哪一份。

## 手动清空自动选择

如果需要让所有课表仅下发而不自动切换，可在仓库本地运行：

```bash
python .github/scripts/select_schedule.py --clear-selection
```

该命令会把 `课程表/` 中所有 JSON 的 `yes.id` 设为 `0`，并同步重建 `manifest.json`。之后提交并推送修改即可。

## 公告

“发布集控公告”工作流保持不变。它只更新 `manifest.json` 中的公告命令，不会修改 `课程表/` 内的文件或其 `yes.id` 参数。
