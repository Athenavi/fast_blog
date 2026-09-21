/**
 * 轻量表单校验
 *
 * 前台表单此前各自手写 `validate()`，只在页面底部提示「第一个」错误：
 * 用户不知道是哪个字段出了问题，读屏也无法与输入框关联。这里统一为「字段 → 规则」：
 *
 * - `validate(rules)` 一次校验全部字段，返回是否通过，并在 `errors` 里按字段给出文案
 * - `fieldProps(field)` 给输入框生成 `aria-invalid` / `aria-describedby`（配合 `errorId()`）
 * - `clearField(field)` 在用户重新输入时清掉该字段错误，避免「改完了红字还在」
 *
 * 文案由调用方做 i18n（规则函数返回已翻译的字符串或 `null`）。
 */
export function useFormErrors() {
  const errors = ref<Record<string, string>>({})

  /** 字段错误提示的 DOM id，供 `aria-describedby` 引用 */
  function errorId(field: string): string {
    return `field-error-${field}`
  }

  /** 输入框的无障碍属性；无错误时返回空对象，不额外输出属性 */
  function fieldProps(field: string): Record<string, string> {
    return errors.value[field]
      ? {'aria-invalid': 'true', 'aria-describedby': errorId(field)}
      : {}
  }

  /** 校验全部字段：规则返回非空字符串视为错误 */
  function validate(rules: Record<string, () => string | null>): boolean {
    const next: Record<string, string> = {}
    for (const [field, rule] of Object.entries(rules)) {
      const message = rule()
      if (message) next[field] = message
    }
    errors.value = next
    return Object.keys(next).length === 0
  }

  /** 重新输入时清除该字段的错误 */
  function clearField(field: string): void {
    if (!errors.value[field]) return
    const next = {...errors.value}
    delete next[field]
    errors.value = next
  }

  function clearAll(): void {
    errors.value = {}
  }

  return {errors, validate, clearField, clearAll, errorId, fieldProps}
}
