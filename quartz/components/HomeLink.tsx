import { QuartzComponent, QuartzComponentConstructor, QuartzComponentProps } from "./types"
import { classNames } from "../util/lang"

interface Options {
  url: string
  label: string
}

const defaultOptions: Options = {
  url: "https://soonhaeng.up.railway.app/",
  label: "← 순행투자자문 홈",
}

export default ((userOpts?: Partial<Options>) => {
  const opts = { ...defaultOptions, ...userOpts }
  const HomeLink: QuartzComponent = ({ displayClass }: QuartzComponentProps) => {
    return (
      <a href={opts.url} class={classNames(displayClass, "home-link")}>
        {opts.label}
      </a>
    )
  }

  HomeLink.css = `
.home-link {
  font-size: 0.8rem;
  color: var(--gray);
  text-decoration: none;
  white-space: nowrap;
}
.home-link:hover {
  color: var(--secondary);
}
`
  return HomeLink
}) satisfies QuartzComponentConstructor
