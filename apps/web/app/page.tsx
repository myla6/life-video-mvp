import Link from "next/link"

export default function HomePage() {
  return (
    <main className="flex flex-1 flex-col">
      <header className="border-b border-rose-100 bg-[#FFF5F5]">
        <div className="mx-auto flex max-w-3xl items-center justify-between px-6 py-4">
          <span className="text-lg font-semibold text-rose-900">life-video</span>
          <span className="text-sm text-rose-700/70">生活纪念短片</span>
        </div>
      </header>

      <section className="mx-auto flex w-full max-w-3xl flex-1 flex-col justify-center px-6 py-16">
        <p className="mb-3 text-sm font-medium text-rose-600">MVP · 宝宝满月</p>
        <h1 className="mb-4 text-4xl font-bold tracking-tight text-rose-950">
          上传照片，一键生成满月纪念短片
        </h1>
        <p className="mb-10 max-w-xl text-lg leading-relaxed text-rose-900/75">
          选择模板、填写宝宝信息、挑选背景音乐。照片越多，片长自然越长，竖屏
          720×1280，适合发朋友圈和家庭群。
        </p>

        <div className="flex flex-wrap gap-4">
          <Link
            href="/create/baby-moon"
            className="inline-flex items-center rounded-full bg-rose-600 px-6 py-3 text-base font-medium text-white shadow-sm transition hover:bg-rose-700"
          >
            开始制作 · 宝宝满月
          </Link>
        </div>

        <ul className="mt-12 grid gap-3 text-sm text-rose-900/70 sm:grid-cols-3">
          <li className="rounded-2xl border border-rose-100 bg-white/70 px-4 py-3">
            5～15 张照片
          </li>
          <li className="rounded-2xl border border-rose-100 bg-white/70 px-4 py-3">
            可选 0～2 段短视频
          </li>
          <li className="rounded-2xl border border-rose-100 bg-white/70 px-4 py-3">
            3 首内置 BGM
          </li>
        </ul>
      </section>
    </main>
  )
}
