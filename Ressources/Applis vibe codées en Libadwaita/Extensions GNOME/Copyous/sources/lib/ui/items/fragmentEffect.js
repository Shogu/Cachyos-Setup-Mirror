import Clutter from 'gi://Clutter';
import Cogl from 'gi://Cogl';
import Shell from 'gi://Shell';

import { registerClass } from '../../common/gjs.js';

var __decorate =
	(this && this.__decorate) ||
	function (decorators, target, key, desc) {
		var c = arguments.length,
			r = c < 3 ? target : desc === null ? (desc = Object.getOwnPropertyDescriptor(target, key)) : desc,
			d;
		if (typeof Reflect === 'object' && typeof Reflect.decorate === 'function')
			r = Reflect.decorate(decorators, target, key, desc);
		else
			for (var i = decorators.length - 1; i >= 0; i--)
				if ((d = decorators[i])) r = (c < 3 ? d(r) : c > 3 ? d(target, key, r) : d(target, key)) || r;
		return (c > 3 && r && Object.defineProperty(target, key, r), r);
	};

export function createFragmentEffect(getShader) {
	if (!Shell.GLSLEffect) {
		const ShaderEffect = Clutter.ShaderEffect;
		let CopyousFragmentEffect51 = class CopyousFragmentEffect51 extends ShaderEffect {
			vfunc_get_static_snippet() {
				const { declarations, code } = getShader();
				const snippet = Cogl.Snippet.new(Cogl.SnippetHook.FRAGMENT, declarations, null);
				snippet.set_replace(code);
				return snippet;
			}

			setUniform(name, values) {
				this.set_uniform_float(name, values.length, values);
			}
		};
		CopyousFragmentEffect51 = __decorate([registerClass()], CopyousFragmentEffect51);
		return CopyousFragmentEffect51;
	}
	let CopyousFragmentEffectLegacy = class CopyousFragmentEffectLegacy extends Shell.GLSLEffect {
		vfunc_build_pipeline() {
			const { declarations, code } = getShader();
			this.add_glsl_snippet(Cogl.SnippetHook.FRAGMENT, declarations, code, true);
		}

		setUniform(name, values) {
			this.set_uniform_float(this.get_uniform_location(name), values.length, values);
		}
	};
	CopyousFragmentEffectLegacy = __decorate([registerClass()], CopyousFragmentEffectLegacy);
	return CopyousFragmentEffectLegacy;
}
