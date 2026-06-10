"use client";
import { setLang, useLang } from "@/lib/names";

/** 名称语言切换(中文/English),全站生效,localStorage 记忆。 */
export default function LangSelect() {
  const lang = useLang();
  return (
    <div className="segmented" title="名称语言 / Name language">
      <button className={lang === "zh" ? "active" : ""} onClick={() => setLang("zh")}>中</button>
      <button className={lang === "en" ? "active" : ""} onClick={() => setLang("en")}>EN</button>
    </div>
  );
}
