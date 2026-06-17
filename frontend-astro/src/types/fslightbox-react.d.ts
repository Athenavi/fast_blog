declare module 'fslightbox-react' {
  import type { FC, ReactNode } from 'react'

  interface FsLightboxProps {
    toggler: boolean
    sources: (string | ReactNode)[]
    sourceIndex?: number
    slide?: number
    openOnMount?: boolean
    type?: 'image' | 'video' | 'youtube'
    types?: string[]
    maxSourceWidth?: number
    maxSourceHeight?: number
    maxYoutubeVideoDimensions?: { width: number; height: number }
    slideDistance?: number
    sourceMargin?: number
    disableSlideSwiping?: boolean
    loadOnlyCurrentSource?: boolean
    useDialog?: boolean
    exitFullscreenOnClose?: boolean
    onOpen?: () => void
    onShow?: () => void
    onClose?: () => void
    onSourceLoad?: (lightbox: any, source: HTMLElement, index: number) => void
    autoplay?: boolean
    autoplays?: (boolean | number)[]
    videosPosters?: string[]
    customClasses?: string[]
    customAttributes?: Record<string, string>[]
  }

  const FsLightbox: FC<FsLightboxProps>
  export default FsLightbox
}
