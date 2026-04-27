declare module 'tocbot' {
  interface TocbotOptions {
    tocSelector?: string;
    contentSelector?: string;
    headingSelector?: string;
    positionFixedSelector?: string;
    positionFixedClass?: string;
    fixedSidebarOffset?: number;
    includeHtml?: boolean;
    headingsOffset?: number;
    ignoreSelector?: string;
    linkClass?: string;
    activeLinkClass?: string;
    listClass?: string;
    listItemClass?: string;
    collapseDepth?: number;
    orderedList?: boolean;
    onClick?(e: Event): void;
  }

  interface TocbotInstance {
    init(options: TocbotOptions): void;
    destroy(): void;
  }

  const tocbot: TocbotInstance;
  export default tocbot;
}