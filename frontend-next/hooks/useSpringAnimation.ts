'use client';

import {useEffect, useRef, useState} from 'react';

interface SpringConfig {
    stiffness?: number;     // 弹性系数 (默认: 100)
    damping?: number;       // 阻尼系数 (默认: 10)
    mass?: number;          // 质量 (默认: 1)
    precision?: number;     // 精度阈值 (默认: 0.01)
}

interface SpringState {
    position: number;
    velocity: number;
    target: number;
    isActive: boolean;
}

interface UseSpringAnimationReturn {
    value: number;
    setTarget: (target: number) => void;
    isActive: boolean;
    reset: () => void;
}

/**
 * 自定义弹簧动画Hook
 * 基于胡克定律和阻尼振动实现物理真实的动画效果
 */
export function useSpringAnimation(
    initialValue: number = 0,
    config: SpringConfig = {}
): UseSpringAnimationReturn {
    const {
        stiffness = 100,
        damping = 10,
        mass = 1,
        precision = 0.01
    } = config;

    const [springState, setSpringState] = useState<SpringState>({
        position: initialValue,
        velocity: 0,
        target: initialValue,
        isActive: false
    });

    const animationRef = useRef<number | null>(null);
    const lastTimeRef = useRef<number>(0);

    // 弹簧物理计算核心函数
    const updateSpring = (currentTime: number): boolean => {
        if (!springState.isActive) return false;

        const deltaTime = Math.min((currentTime - lastTimeRef.current) / 1000, 1/60);
        lastTimeRef.current = currentTime;

        const { position, velocity, target } = springState;
        
        // 胡克定律: F = -k * x (恢复力)
        const displacement = position - target;
        const springForce = -stiffness * displacement;
        
        // 阻尼力: F = -c * v
        const dampingForce = -damping * velocity;
        
        // 牛顿第二定律: F = m * a
        const acceleration = (springForce + dampingForce) / mass;
        
        // 更新速度和位置
        const newVelocity = velocity + acceleration * deltaTime;
        const newPosition = position + newVelocity * deltaTime;

        // 检查是否应该停止动画
        const isAtRest = 
            Math.abs(newPosition - target) < precision && 
            Math.abs(newVelocity) < precision;

        setSpringState(prev => ({
            position: isAtRest ? target : newPosition,
            velocity: isAtRest ? 0 : newVelocity,
            target: prev.target,
            isActive: !isAtRest
        }));

        return !isAtRest;
    };

    // 动画循环
    useEffect(() => {
        if (!springState.isActive) {
            if (animationRef.current) {
                cancelAnimationFrame(animationRef.current);
                animationRef.current = null;
            }
            return;
        }

        const animate = (timestamp: number) => {
            const shouldContinue = updateSpring(timestamp);
            if (shouldContinue && animationRef.current !== null) {
                animationRef.current = requestAnimationFrame(animate);
            } else {
                setSpringState(prev => ({ ...prev, isActive: false }));
            }
        };

        animationRef.current = requestAnimationFrame(animate);
        
        return () => {
            if (animationRef.current) {
                cancelAnimationFrame(animationRef.current);
            }
        };
    }, [springState.isActive, stiffness, damping, mass, precision]);

    const setTarget = (target: number) => {
        setSpringState(prev => ({
            ...prev,
            target,
            isActive: true
        }));
        lastTimeRef.current = performance.now();
    };

    const reset = () => {
        if (animationRef.current) {
            cancelAnimationFrame(animationRef.current);
            animationRef.current = null;
        }
        setSpringState({
            position: initialValue,
            velocity: 0,
            target: initialValue,
            isActive: false
        });
    };

    return {
        value: springState.position,
        setTarget,
        isActive: springState.isActive,
        reset
    };
}

/**
 * 二维弹簧动画Hook
 */
export function useSpringAnimation2D(
    initialX: number = 0,
    initialY: number = 0,
    config: SpringConfig = {}
) {
    const xSpring = useSpringAnimation(initialX, config);
    const ySpring = useSpringAnimation(initialY, config);

    return {
        x: xSpring.value,
        y: ySpring.value,
        setTarget: (x: number, y: number) => {
            xSpring.setTarget(x);
            ySpring.setTarget(y);
        },
        isActive: xSpring.isActive || ySpring.isActive,
        reset: () => {
            xSpring.reset();
            ySpring.reset();
        }
    };
}

/**
 * 预设的弹簧配置
 */
export const springPresets = {
    // 柔软弹簧 - 慢速、大幅度摆动
    gentle: { stiffness: 50, damping: 5, mass: 1 },
    
    // 默认弹簧 - 平衡的响应
    default: { stiffness: 100, damping: 10, mass: 1 },
    
    // 快速弹簧 - 快速响应、小幅振动
    snappy: { stiffness: 200, damping: 20, mass: 1 },
    
    // 弹跳弹簧 - 明显的过冲效果
    bouncy: { stiffness: 80, damping: 3, mass: 1 },
    
    // 粘滞弹簧 - 很慢的响应
    sluggish: { stiffness: 30, damping: 15, mass: 1 },
    
    // 黑洞吸附效果 - 极强吸引力
    blackhole: { stiffness: 300, damping: 25, mass: 0.5 },
    
    // 长时间黑洞吸附 - 更慢更丝滑的动画
    blackholeLong: { stiffness: 150, damping: 15, mass: 1, precision: 0.001 },
    
    // 从点击点开始的吸附效果
    clickAttract: { stiffness: 200, damping: 18, mass: 0.8, precision: 0.005 }
} as const;

// 类型导出
export type SpringPreset = keyof typeof springPresets;