import React, { useState, useEffect } from 'react';

interface EditDialogProps {
    title: string;
    value: string;
    nodeId: string;
    field: 'input' | 'output';
    sessionId: string;
    onSave: (nodeId: string, field: 'input' | 'output', sessionId: string, value: string) => void;
    onCancel: () => void;
}

export const EditDialog: React.FC<EditDialogProps> = ({ 
    title, 
    value, 
    nodeId, 
    field, 
    sessionId, 
    onSave, 
    onCancel 
}) => {
    const [text, setText] = useState(value);

    useEffect(() => {
        setText(value);
    }, [value]);

    const handleSave = () => {
        onSave(nodeId, field, sessionId, text);
    };

    return (
        <div
            style={{
                position: 'fixed',
                top: 0,
                left: 0,
                right: 0,
                bottom: 0,
                backgroundColor: 'rgba(0, 0, 0, 0.5)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                zIndex: 1000,
            }}
            onClick={(e: React.MouseEvent) => {
                if (e.target === e.currentTarget) {
                    onCancel();
                }
            }}
        >
            <div
                style={{
                    backgroundColor: '#2c2c2c',
                    borderRadius: '8px',
                    padding: '20px',
                    width: '80%',
                    maxWidth: '800px',
                    maxHeight: '80vh',
                    display: 'flex',
                    flexDirection: 'column',
                    gap: '16px',
                }}
                onClick={(e: React.MouseEvent) => e.stopPropagation()}
            >
                <div style={{ fontSize: '16px', fontWeight: 'bold', color: '#fff' }}>
                    {title}
                </div>
                <textarea
                    value={text}
                    onChange={(e: React.ChangeEvent<HTMLTextAreaElement>) => setText(e.target.value)}
                    style={{
                        width: '100%',
                        height: '300px',
                        padding: '12px',
                        backgroundColor: '#1e1e1e',
                        color: '#fff',
                        border: '1px solid #444',
                        borderRadius: '4px',
                        resize: 'vertical',
                        fontFamily: 'monospace',
                        fontSize: '14px',
                        lineHeight: '1.5',
                    }}
                />
                <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '8px' }}>
                    <button
                        onClick={onCancel}
                        style={{
                            padding: '8px 16px',
                            backgroundColor: '#444',
                            color: '#fff',
                            border: 'none',
                            borderRadius: '4px',
                            cursor: 'pointer',
                        }}
                    >
                        Cancel
                    </button>
                    <button
                        onClick={handleSave}
                        style={{
                            padding: '8px 16px',
                            backgroundColor: '#007acc',
                            color: '#fff',
                            border: 'none',
                            borderRadius: '4px',
                            cursor: 'pointer',
                        }}
                    >
                        Save
                    </button>
                </div>
            </div>
        </div>
    );
};