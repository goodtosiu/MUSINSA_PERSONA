import React from 'react';
import './PurchasePage.css';

const API_BASE_URL = process.env.REACT_APP_API_BASE_URL || 'http://127.0.0.1:5000';

const PurchasePage = ({ selectedItems, onBack, bgPath, persona }) => {
  const totalPrice = selectedItems.reduce((sum, item) => sum + (item.price || 0), 0);

  const handlePay = async () => {
    try {
      // selectedItems -> backend expected payload
      const payload = {
        persona,
        items: selectedItems
          .filter(it => it && it.product_id && it.category)
          .map(it => ({ category: it.category, product_id: it.product_id }))
      };

      const res = await fetch(`${API_BASE_URL}/api/outfit`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });

      const data = await res.json().catch(() => ({}));

      if (res.status === 201) {
        alert("✅ 결제가 완료되어 아웃핏이 저장되었습니다!");
        return;
      }
      if (res.status === 409) {
        alert("ℹ️ 이미 저장된(중복) 아웃핏입니다.");
        return;
      }
      alert(`❌ 결제/저장 실패: ${data.error || res.status}`);
    } catch (e) {
      alert(`❌ 결제/저장 실패: ${e?.message || e}`);
    }
  };

  return (
    <div className="advanced-collage-layout dark-theme">
      {/* 왼쪽: 캔버스 영역 */}
      <section className="left-canvas-area">
        <div className="canvas-header">
           <span className="outfit-badge">마이 아웃핏</span>
        </div>
        <div className="collage-canvas" 
             style={{ backgroundImage: bgPath ? `url(${bgPath})` : 'none' }}>
          {selectedItems.map((item) => (
            <div key={item.instanceId} className="canvas-item"
                 style={{ 
                   left: `${item.x}px`, 
                   top: `${item.y}px`, 
                   transform: `scale(${item.scale})`, 
                   zIndex: item.zIndex 
                 }}>
              <img src={item.img_url} alt="" draggable="false" />
            </div>
          ))}
        </div>
      </section>

      {/* [수정] 중앙 로고 영역(center-divider-area)이 삭제되었습니다. */}

      {/* 오른쪽: 상세 내역 */}
      <section className="right-list-area purchase-sidebar">
        <div className="top-section">
          <h2 className="sidebar-title">선택 상품</h2>
          <div className="purchase-list"> 
            {selectedItems.map((item) => (
              <div key={item.instanceId} className="purchase-item-card">
                <div className="item-img-container">
                  <img src={item.img_url} alt="" />
                </div>
                <div className="item-text-info">
                  <p className="item-name">{item.product_name}</p>
                  <p className="item-price">{item.price?.toLocaleString()}원</p>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* 하단 버튼 섹션 (고정) */}
        <div className="action-button-group purchase-actions">
          <button className="coupon-btn" onClick={() => alert("사용 가능한 쿠폰이 없습니다.")}>
            쿠폰 사용
          </button>
          <button className="pay-btn-white" onClick={handlePay}>
            {totalPrice.toLocaleString()}원 결제하기
          </button>
          <button className="back-link-text" onClick={onBack}>
            수정하러 가기
          </button>
        </div>
      </section>
    </div>
  );
};

export default PurchasePage;