import { Modal } from "antd";

function ErrorModal({ open, message, onClose }) {
  return (
    <Modal
      open={open}
      title="操作失败"
      onOk={onClose}
      onCancel={onClose}
      okText="确认"
      cancelButtonProps={{ style: { display: "none" } }}
    >
      {message}
    </Modal>
  );
}

export default ErrorModal;
