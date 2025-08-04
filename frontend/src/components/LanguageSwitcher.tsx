import React from 'react';
import { IconButton, Menu, MenuItem, Tooltip } from '@mui/material';
import Language from '@mui/icons-material/Language';
import { useTranslation } from 'react-i18next';

export const LanguageSwitcher: React.FC = () => {
  const { i18n, t } = useTranslation();
  const [anchorEl, setAnchorEl] = React.useState<null | HTMLElement>(null);
  const open = Boolean(anchorEl);

  const handleClick = (event: React.MouseEvent<HTMLElement>) => {
    setAnchorEl(event.currentTarget);
  };

  const handleClose = () => {
    setAnchorEl(null);
  };

  const handleLanguageChange = (language: string) => {
    i18n.changeLanguage(language);
    handleClose();
  };


  return (
    <>
      <Tooltip title={`${t('language.switchTo', { language: i18n.language === 'en' ? 'Deutsch' : 'English' })}`}>
        <IconButton 
          onClick={handleClick}
          size="small"
          sx={{ color: 'inherit' }}
        >
          <Language />
        </IconButton>
      </Tooltip>
      <Menu
        anchorEl={anchorEl}
        open={open}
        onClose={handleClose}
        anchorOrigin={{
          vertical: 'bottom',
          horizontal: 'right',
        }}
        transformOrigin={{
          vertical: 'top',
          horizontal: 'right',
        }}
      >
        <MenuItem 
          onClick={() => handleLanguageChange('en')}
          selected={i18n.language === 'en'}
        >
          {t('language.english')}
        </MenuItem>
        <MenuItem 
          onClick={() => handleLanguageChange('de')}
          selected={i18n.language === 'de'}
        >
          {t('language.german')}
        </MenuItem>
      </Menu>
    </>
  );
};