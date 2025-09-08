/**
 * Custom Gauge Chart Implementation for AnomalySNMP
 * Provides a more sophisticated gauge visualization with color zones
 */

class AnomalyGauge {
    constructor(canvasId, options = {}) {
        this.canvas = document.getElementById(canvasId);
        this.ctx = this.canvas.getContext('2d');
        this.value = 0;
        this.animationId = null;
        
        // Default options
        this.options = {
            min: 0,
            max: 1,
            size: 200,
            thickness: 20,
            startAngle: -Math.PI,
            endAngle: 0,
            backgroundColor: '#ecf0f1',
            textColor: '#2c3e50',
            fontSize: 24,
            fontFamily: 'Segoe UI, sans-serif',
            showValue: true,
            showLabel: true,
            label: 'S-Score',
            animationDuration: 1000,
            colorZones: [
                { min: 0.0, max: 0.4, color: '#e74c3c', label: 'Critico' },
                { min: 0.4, max: 0.6, color: '#ff6b35', label: 'Attenzione' },
                { min: 0.6, max: 0.8, color: '#f39c12', label: 'Buono' },
                { min: 0.8, max: 1.0, color: '#27ae60', label: 'Eccellente' }
            ],
            ...options
        };
        
        this.setupCanvas();
        this.draw();
    }
    
    setupCanvas() {
        const size = this.options.size;
        this.canvas.width = size;
        this.canvas.height = size * 0.6; // Semi-circle
        this.canvas.style.width = size + 'px';
        this.canvas.style.height = (size * 0.6) + 'px';
        
        // High DPI support
        const dpr = window.devicePixelRatio || 1;
        this.canvas.width = size * dpr;
        this.canvas.height = size * 0.6 * dpr;
        this.ctx.scale(dpr, dpr);
    }
    
    getColorForValue(value) {
        for (const zone of this.options.colorZones) {
            if (value >= zone.min && value <= zone.max) {
                return zone;
            }
        }
        return this.options.colorZones[0]; // Default to first zone
    }
    
    drawBackground() {
        const { size, thickness, startAngle, endAngle, backgroundColor } = this.options;
        const centerX = size / 2;
        const centerY = size / 2;
        const radius = (size / 2) - thickness;
        
        this.ctx.beginPath();
        this.ctx.arc(centerX, centerY, radius, startAngle, endAngle);
        this.ctx.lineWidth = thickness;
        this.ctx.strokeStyle = backgroundColor;
        this.ctx.lineCap = 'round';
        this.ctx.stroke();
    }
    
    drawColorZones() {
        const { size, thickness, startAngle, endAngle, colorZones } = this.options;
        const centerX = size / 2;
        const centerY = size / 2;
        const radius = (size / 2) - thickness;
        const totalAngle = endAngle - startAngle;
        
        // Draw background zones with reduced opacity
        colorZones.forEach(zone => {
            const zoneStartAngle = startAngle + (zone.min * totalAngle);
            const zoneEndAngle = startAngle + (zone.max * totalAngle);
            
            this.ctx.beginPath();
            this.ctx.arc(centerX, centerY, radius, zoneStartAngle, zoneEndAngle);
            this.ctx.lineWidth = thickness * 0.3;
            this.ctx.strokeStyle = zone.color + '40'; // 25% opacity
            this.ctx.lineCap = 'round';
            this.ctx.stroke();
        });
    }
    
    drawValue() {
        const { size, thickness, startAngle, endAngle } = this.options;
        const centerX = size / 2;
        const centerY = size / 2;
        const radius = (size / 2) - thickness;
        const totalAngle = endAngle - startAngle;
        const valueAngle = startAngle + (this.value * totalAngle);
        
        const colorZone = this.getColorForValue(this.value);
        
        // Draw value arc
        this.ctx.beginPath();
        this.ctx.arc(centerX, centerY, radius, startAngle, valueAngle);
        this.ctx.lineWidth = thickness;
        this.ctx.strokeStyle = colorZone.color;
        this.ctx.lineCap = 'round';
        this.ctx.stroke();
        
        // Draw needle/indicator
        const needleX = centerX + Math.cos(valueAngle) * (radius - thickness / 2);
        const needleY = centerY + Math.sin(valueAngle) * (radius - thickness / 2);
        
        this.ctx.beginPath();
        this.ctx.arc(needleX, needleY, thickness / 3, 0, 2 * Math.PI);
        this.ctx.fillStyle = colorZone.color;
        this.ctx.fill();
        
        // Add glow effect
        this.ctx.shadowColor = colorZone.color;
        this.ctx.shadowBlur = 10;
        this.ctx.beginPath();
        this.ctx.arc(needleX, needleY, thickness / 4, 0, 2 * Math.PI);
        this.ctx.fillStyle = '#ffffff';
        this.ctx.fill();
        this.ctx.shadowBlur = 0;
    }
    
    drawText() {
        const { size, fontSize, fontFamily, textColor, showValue, showLabel, label } = this.options;
        const centerX = size / 2;
        const centerY = size / 2;
        const colorZone = this.getColorForValue(this.value);
        
        this.ctx.textAlign = 'center';
        this.ctx.fillStyle = textColor;
        
        if (showValue) {
            // Main value
            this.ctx.font = `bold ${fontSize}px ${fontFamily}`;
            const percentage = Math.round(this.value * 100);
            this.ctx.fillText(`${percentage}%`, centerX, centerY + 10);
            
            // Level label
            this.ctx.font = `${fontSize * 0.5}px ${fontFamily}`;
            this.ctx.fillStyle = colorZone.color;
            this.ctx.fillText(colorZone.label, centerX, centerY + 35);
        }
        
        if (showLabel) {
            this.ctx.font = `${fontSize * 0.6}px ${fontFamily}`;
            this.ctx.fillStyle = textColor;
            this.ctx.fillText(label, centerX, centerY - 40);
        }
    }
    
    draw() {
        // Clear canvas
        this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);
        
        // Draw components
        this.drawBackground();
        this.drawColorZones();
        this.drawValue();
        this.drawText();
    }
    
    setValue(newValue, animate = true) {
        const clampedValue = Math.max(this.options.min, Math.min(this.options.max, newValue));
        
        if (animate) {
            this.animateToValue(clampedValue);
        } else {
            this.value = clampedValue;
            this.draw();
        }
    }
    
    animateToValue(targetValue) {
        if (this.animationId) {
            cancelAnimationFrame(this.animationId);
        }
        
        const startValue = this.value;
        const startTime = performance.now();
        const duration = this.options.animationDuration;
        
        const animate = (currentTime) => {
            const elapsed = currentTime - startTime;
            const progress = Math.min(elapsed / duration, 1);
            
            // Easing function (ease-out)
            const easeOut = 1 - Math.pow(1 - progress, 3);
            
            this.value = startValue + (targetValue - startValue) * easeOut;
            this.draw();
            
            if (progress < 1) {
                this.animationId = requestAnimationFrame(animate);
            } else {
                this.animationId = null;
            }
        };
        
        this.animationId = requestAnimationFrame(animate);
    }
    
    updateTheme(isDark) {
        this.options.textColor = isDark ? '#f0f0f0' : '#2c3e50';
        this.options.backgroundColor = isDark ? '#404040' : '#ecf0f1';
        this.draw();
    }
    
    resize(newSize) {
        this.options.size = newSize;
        this.setupCanvas();
        this.draw();
    }
    
    destroy() {
        if (this.animationId) {
            cancelAnimationFrame(this.animationId);
        }
    }
}

// Export for use in other modules
if (typeof window !== 'undefined') {
    window.AnomalyGauge = AnomalyGauge;
}

if (typeof module !== 'undefined' && module.exports) {
    module.exports = AnomalyGauge;
}