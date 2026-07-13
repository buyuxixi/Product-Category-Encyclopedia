"use client";

import { useEffect, useMemo, useState } from "react";
import { categories, glossary, type Category } from "./data";

const navItems = [
  { id: "overview", label: "总览" },
  { id: "categories", label: "品类" },
  { id: "glossary", label: "术语" },
  { id: "method", label: "研究说明" },
];

function matchesCategory(category: Category, value: string) {
  const haystack = [
    category.name,
    category.english,
    category.descriptor,
    category.summary,
    category.definition,
    ...category.tags,
    ...category.scenarios,
  ]
    .join(" ")
    .toLowerCase();
  return haystack.includes(value);
}

export default function EncyclopediaClient() {
  const [query, setQuery] = useState("");
  const [selectedSlug, setSelectedSlug] = useState<string | null>(null);
  const [activeSection, setActiveSection] = useState("overview");
  const [showAllTerms, setShowAllTerms] = useState(false);

  const selectedCategory = categories.find((item) => item.slug === selectedSlug);
  const filteredCategories = useMemo(() => {
    const value = query.trim().toLowerCase();
    if (!value) return categories;
    return categories.filter((category) => matchesCategory(category, value));
  }, [query]);

  const visibleGlossary = showAllTerms ? glossary : glossary.slice(0, 6);

  useEffect(() => {
    function onKeyDown(event: KeyboardEvent) {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k") {
        event.preventDefault();
        document.getElementById("global-search")?.focus();
      }
      if (event.key === "Escape") setSelectedSlug(null);
    }
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, []);

  function scrollTo(section: string) {
    document.getElementById(section)?.scrollIntoView({ behavior: "smooth", block: "start" });
    setActiveSection(section);
  }

  function openCategory(category: Category) {
    setSelectedSlug(category.slug);
  }

  function openNextCategory(category: Category) {
    const index = categories.findIndex((item) => item.slug === category.slug);
    setSelectedSlug(categories[(index + 1) % categories.length].slug);
  }

  return (
    <div className="site-shell">
      <header className="site-header">
        <button className="brand" type="button" onClick={() => scrollTo("overview")} aria-label="回到总览">
          <span className="brand-mark">P</span>
          <span className="brand-copy">
            <strong>产品品类百科</strong>
            <small>CATEGORY INTELLIGENCE</small>
          </span>
        </button>

        <nav className="header-nav" aria-label="主导航">
          {navItems.map((item) => (
            <button
              key={item.id}
              type="button"
              className={activeSection === item.id ? "is-active" : ""}
              onClick={() => scrollTo(item.id)}
            >
              {item.label}
            </button>
          ))}
        </nav>

        <div className="header-meta">
          <span className="live-dot" aria-hidden="true" />
          <span>研究更新于 2026.07</span>
        </div>
      </header>

      <div className="workspace">
        <aside className="category-rail" aria-label="品类导航">
          <div className="rail-label">INDEX / 05</div>
          <div className="rail-list">
            {categories.map((category) => (
              <button
                type="button"
                key={category.slug}
                className={selectedSlug === category.slug ? "rail-item is-selected" : "rail-item"}
                onClick={() => openCategory(category)}
              >
                <span className="rail-number">{category.index}</span>
                <span>{category.name}</span>
              </button>
            ))}
          </div>
          <div className="rail-footer">
            <span className="rail-footer-line" />
            <span>PUBLIC EDITION</span>
          </div>
        </aside>

        <main className="site-main">
          <section className="hero-section" id="overview">
            <div className="hero-panel">
              <div className="hero-copy">
                <div className="eyebrow">PRODUCT KNOWLEDGE BASE <span>/</span> 公开版</div>
                <h1>
                  把复杂品类，
                  <br />
                  <em>讲成清晰决策。</em>
                </h1>
                <p>
                  从原理、参数到真实使用场景，沿着一条更容易理解的路径，找到真正适合自己的产品。
                </p>
                <div className="hero-actions">
                  <button type="button" className="primary-button" onClick={() => scrollTo("categories")}>
                    浏览五大品类 <span aria-hidden="true">↗</span>
                  </button>
                  <span className="hero-note">研究框架 v1.0 · 持续整理中</span>
                </div>
              </div>
              <div className="hero-visual" aria-hidden="true">
                <div className="visual-orbit orbit-one" />
                <div className="visual-orbit orbit-two" />
                <div className="visual-orbit orbit-three" />
                <div className="visual-node node-one">01</div>
                <div className="visual-node node-two">05</div>
                <div className="visual-axis axis-x" />
                <div className="visual-axis axis-y" />
              </div>
              <div className="hero-corner-label">从功能参数 → 使用场景 → 选择判断</div>
            </div>

            <aside className="research-panel">
              <div className="panel-kicker">研究路径</div>
              <div className="signal-ring" aria-hidden="true">
                <div className="signal-ring-inner">
                  <strong>05</strong>
                  <span>大品类</span>
                </div>
              </div>
              <div className="panel-rule" />
              <div className="panel-stat">
                <span>内容状态</span>
                <strong>持续更新</strong>
              </div>
              <div className="panel-stat">
                <span>研究维度</span>
                <strong>原理 · 场景 · 边界</strong>
              </div>
              <button type="button" className="text-button" onClick={() => scrollTo("method")}>
                了解研究方法 <span aria-hidden="true">→</span>
              </button>
            </aside>
          </section>

          <section className="search-section" aria-label="搜索品类">
            <div className="search-icon" aria-hidden="true" />
            <input
              id="global-search"
              type="search"
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="搜索品类、术语或使用场景"
              aria-label="搜索品类、术语或使用场景"
            />
            <kbd>⌘ K</kbd>
            {query && (
              <button type="button" className="clear-search" onClick={() => setQuery("")} aria-label="清除搜索">
                ×
              </button>
            )}
          </section>

          <section className="categories-section" id="categories">
            <div className="section-heading">
              <div>
                <div className="eyebrow">THE INDEX</div>
                <h2>五大品类 <span>/ 05</span></h2>
              </div>
              <div className="result-summary">
                {query ? `找到 ${filteredCategories.length} 个匹配品类` : "先看懂，再比较"}
              </div>
            </div>

            {filteredCategories.length > 0 ? (
              <div className="category-grid">
                {filteredCategories.map((category) => (
                  <button
                    type="button"
                    className={`category-card tone-${category.statusTone}`}
                    key={category.slug}
                    onClick={() => openCategory(category)}
                  >
                    <div className="card-topline">
                      <span className="card-index">{category.index} / {category.english}</span>
                      <span className="card-status"><i />{category.status}</span>
                    </div>
                    <div className="card-body">
                      <h3>{category.name}</h3>
                      <p>{category.summary}</p>
                    </div>
                    <div className="card-bottomline">
                      <div className="chip-list">
                        {category.tags.slice(0, 2).map((tag) => <span key={tag}>{tag}</span>)}
                      </div>
                      <span className="card-arrow" aria-hidden="true">↗</span>
                    </div>
                  </button>
                ))}
              </div>
            ) : (
              <div className="empty-state">
                <strong>没有找到匹配的品类</strong>
                <span>试试“温度”“提醒”或“人体工学”</span>
                <button type="button" onClick={() => setQuery("")}>清除搜索</button>
              </div>
            )}
          </section>

          <section className="insight-grid">
            <div className="insight-panel update-panel">
              <div className="panel-heading">
                <div>
                  <div className="eyebrow">TODAY&apos;S BRIEF</div>
                  <h2>今日速览</h2>
                </div>
                <span className="panel-date">13 JUL 2026</span>
              </div>
              <div className="brief-list">
                <button type="button" onClick={() => openCategory(categories[0])}>
                  <span className="brief-number">01</span>
                  <span><strong>热敷不是越热越好</strong><small>先看温度、覆盖面积与控温方式</small></span>
                  <span className="brief-arrow">→</span>
                </button>
                <button type="button" onClick={() => openCategory(categories[2])}>
                  <span className="brief-number">02</span>
                  <span><strong>夜灯要放在场景里判断</strong><small>亮度、距离和使用时序同样重要</small></span>
                  <span className="brief-arrow">→</span>
                </button>
                <button type="button" onClick={() => openCategory(categories[4])}>
                  <span className="brief-number">03</span>
                  <span><strong>坐垫改变的不只是柔软度</strong><small>支撑点会继续影响角度与视线</small></span>
                  <span className="brief-arrow">→</span>
                </button>
              </div>
            </div>

            <div className="insight-panel glossary-panel" id="glossary">
              <div className="panel-heading">
                <div>
                  <div className="eyebrow">QUICK GLOSSARY</div>
                  <h2>热门术语</h2>
                </div>
                <span className="term-count">{glossary.length} TERMS</span>
              </div>
              <div className="glossary-list">
                {visibleGlossary.map((item) => (
                  <button type="button" className="glossary-item" key={item.term} onClick={() => setQuery(item.term)}>
                    <strong>{item.term}</strong>
                    <span>{item.note}</span>
                  </button>
                ))}
              </div>
              <button type="button" className="text-button glossary-more" onClick={() => setShowAllTerms((value) => !value)}>
                {showAllTerms ? "收起术语" : "查看全部术语"} <span aria-hidden="true">↘</span>
              </button>
            </div>
          </section>

          <section className="method-section" id="method">
            <div className="method-intro">
              <div className="eyebrow">HOW TO READ</div>
              <h2>先问三个问题，<br /><em>再看产品参数。</em></h2>
            </div>
            <div className="method-steps">
              <div className="method-step"><span>01</span><strong>它解决什么场景？</strong><p>从真实使用动作出发，不把参数直接等同于价值。</p></div>
              <div className="method-step"><span>02</span><strong>关键变量是什么？</strong><p>找到温度、亮度、强度、支撑等真正影响体验的变量。</p></div>
              <div className="method-step"><span>03</span><strong>边界和代价在哪里？</strong><p>把安全、维护、耗材与误用风险一起放进判断。</p></div>
            </div>
          </section>

          <footer className="site-footer">
            <span>产品品类百科 · CATEGORY INTELLIGENCE</span>
            <span>公开知识库 / 仅作研究参考，不替代专业医疗建议</span>
          </footer>
        </main>
      </div>

      {selectedCategory && (
        <div className="detail-backdrop" role="presentation" onMouseDown={() => setSelectedSlug(null)}>
          <section className={`detail-sheet tone-${selectedCategory.statusTone}`} role="dialog" aria-modal="true" aria-labelledby="detail-title" onMouseDown={(event) => event.stopPropagation()}>
            <div className="detail-header">
              <div>
                <div className="eyebrow">{selectedCategory.index} / {selectedCategory.english}</div>
                <h2 id="detail-title">{selectedCategory.name}</h2>
              </div>
              <button type="button" className="close-button" onClick={() => setSelectedSlug(null)} aria-label="关闭详情">×</button>
            </div>
            <p className="detail-summary">{selectedCategory.definition}</p>
            <div className="detail-metrics">
              {selectedCategory.metrics.map((metric) => (
                <div key={metric.label}><span>{metric.label}</span><strong>{metric.value}</strong></div>
              ))}
            </div>
            <div className="detail-columns">
              <div>
                <div className="detail-label">适用场景</div>
                <ul>{selectedCategory.scenarios.map((item) => <li key={item}>{item}</li>)}</ul>
              </div>
              <div>
                <div className="detail-label">选品时可以问</div>
                <ul>{selectedCategory.questions.map((item) => <li key={item}>{item}</li>)}</ul>
              </div>
            </div>
            <div className="detail-sources">
              <span>相关条目</span>
              <div>{selectedCategory.sources.map((item) => <button type="button" key={item} onClick={() => setQuery(item.split(" /")[0])}>{item}</button>)}</div>
            </div>
            <div className="detail-footer">
              <span>内容仅用于品类研究与比较，不替代专业建议。</span>
              <button type="button" className="primary-button" onClick={() => openNextCategory(selectedCategory)}>下一品类 <span aria-hidden="true">→</span></button>
            </div>
          </section>
        </div>
      )}
    </div>
  );
}
