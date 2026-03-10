'use client'

import { Toaster as Sonner, ToasterProps } from 'sonner'

const Toaster = ({ toastOptions, ...props }: ToasterProps) => {
  return (
    <Sonner
      theme="light"
      className="toaster group"
      richColors
      toastOptions={{
        role: 'status',
        'aria-live': 'polite',
        classNames: {
          toast: 'schnappster-toast',
          title: 'schnappster-toast-title',
          description: 'schnappster-toast-description',
        },
        ...toastOptions,
      }}
      style={
        {
          '--width': 'min(420px, calc(100vw - 2rem))',
        } as React.CSSProperties
      }
      {...props}
    />
  )
}

export { Toaster }
