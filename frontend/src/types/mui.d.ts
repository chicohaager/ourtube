declare module '@mui/icons-material' {
  export * from '@mui/icons-material/index';
}

declare module '@mui/icons-material/*' {
  import { SvgIconProps } from '@mui/material/SvgIcon';
  import { ComponentType } from 'react';
  const Icon: ComponentType<SvgIconProps>;
  export default Icon;
}