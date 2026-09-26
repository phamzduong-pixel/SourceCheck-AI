import React from 'react';
import { createPortal } from 'react-dom';
import { useAIPreferences } from '../../hooks/useAIPreferences';

interface DeleteConversationModalProps {
  isOpen: boolean;
  isDeleting: boolean;
  onConfirm: () => void;
  onCancel: () => void;
}

export const DeleteConversationModal: React.FC<DeleteConversationModalProps> = ({
  isOpen,
  isDeleting,
  onConfirm,
  onCancel,
}) => {
  const { t } = useAIPreferences();

  if (!isOpen) return null;

  return createPortal(
    <div className="modal-backdrop" data-testid="delete-conversation-modal-backdrop">
      <div
        className="modal-dialog delete-confirmation-modal"
        role="dialog"
        aria-modal="true"
        aria-labelledby="delete-modal-title"
        data-testid="delete-conversation-modal"
      >
        <div className="modal-header">
          <h3 id="delete-modal-title" className="modal-title">
            {t('chat.deleteConfirmTitle')}
          </h3>
          <button
            type="button"
            className="modal-close-btn"
            onClick={onCancel}
            aria-label={t('common.close')}
            disabled={isDeleting}
          >
            ✕
          </button>
        </div>
        <div className="modal-body">
          <p className="modal-message">{t('chat.deleteConfirmMessage')}</p>
        </div>
        <div className="modal-footer">
          <button
            type="button"
            className="btn-modal-secondary"
            onClick={onCancel}
            disabled={isDeleting}
            data-testid="btn-modal-cancel"
          >
            {t('chat.deleteCancelBtn')}
          </button>
          <button
            type="button"
            className="btn-modal-danger"
            onClick={onConfirm}
            disabled={isDeleting}
            data-testid="btn-modal-confirm"
          >
            {isDeleting ? t('common.loading') : t('chat.deleteConfirmBtn')}
          </button>
        </div>
      </div>
    </div>,
    document.body
  );
};

export default DeleteConversationModal;